#!/bin/sh
# Runs inside the container (needs --privileged for network namespaces and /dev/net/tun).
set -e
INPUT=${1:-examples/grid_16.json}
OUT=emane/build
LOGS=$OUT/logs
mkdir -p "$LOGS"

# Part 1 -> schedule, Part 2 bridge -> EMANE files
python3 schedule_optimizer.py --nodes-file "$INPUT" --json-out $OUT/schedule.json
EXTRA=""
if [ "$BASELINE" = "1" ]; then
    python3 emane/make_baseline.py $OUT/schedule.json $OUT/schedule.json
    EXTRA="--allow-collisions"
fi
python3 emane/bridge.py $OUT/schedule.json --out $OUT $EXTRA --slot-us ${SLOT_US:-1000}

NEMS=$(python3 -c "import json;print(' '.join(str(v['nem_id']) for v in json.load(open('$OUT/nems.json')).values()))")

# One network namespace per radio; eth0 of each sits on a bridge that carries the
# EMANE control multicast (OTA manager + event service).
ip link add br0 type bridge
ip link set br0 up
ip addr add 172.30.0.254/24 dev br0
for i in $NEMS ctl; do
    ns=nem$i; [ "$i" = ctl ] && ns=ctl
    ip netns add $ns
    ip link add v$ns type veth peer name p$ns
    ip link set p$ns master br0 && ip link set p$ns up
    ip link set v$ns netns $ns name eth0
    n=${i#ctl}; n=${n:-253}
    ip netns exec $ns ip addr add 172.30.0.$n/24 dev eth0
    ip netns exec $ns ip link set eth0 multicast on
    ip netns exec $ns ip link set eth0 up
    ip netns exec $ns ip link set lo up
    ip netns exec $ns ip route add 224.0.0.0/4 dev eth0
done

for i in $NEMS; do
    ip netns exec nem$i emane -d -l 3 -f $LOGS/emane$i.log --pidfile $LOGS/emane$i.pid $OUT/platform$i.xml
done
ABS=$(pwd)
(cd $OUT && ip netns exec ctl emaneeventservice -d -l 3 -f $ABS/$LOGS/eventservice.log eventservice.xml)
sleep 3

# push the TDMA schedule to every NEM
ip route add 224.0.0.0/4 dev br0 2>/dev/null || true
emaneevent-tdmaschedule $OUT/tdmaschedule.xml -i br0
sleep 2

sh emane/check_schedule.sh $OUT
sh emane/load_test.sh $OUT
