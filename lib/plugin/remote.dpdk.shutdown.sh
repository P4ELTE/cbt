CMD="sudo killall l2_switch_test"
echo $CMD
ssh -p 11122 brocade2@157.181.167.25 -C $CMD
