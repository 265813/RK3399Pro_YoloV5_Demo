starttime=`date +'%Y-%m-%d %H:%M:%S'`
echo $starttime
./asr_offline_record_sample
endtime=`date +'%Y-%m-%d %H:%M:%S'`
echo $endtime
start_seconds=$(date --date="$starttime" +%s);
end_seconds=$(date --date="$endtime" +%s);
echo "..................... "$((end_seconds-start_seconds))"s"
