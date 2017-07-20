CMD="cd /home/brocade2/vpetya/repos/trunk; ./testL2.sh $1 $2"
echo $CMD
ssh -p 11122 brocade2@157.181.167.25 -C $CMD
