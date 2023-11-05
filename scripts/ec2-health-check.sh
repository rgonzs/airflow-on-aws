#!/bin/bash -xe

#get instance id

instance=$(curl http://169.254.169.254/latest/meta-data/instance-id)

sleep 120

server_role=$(systemctl list-units | grep -E "airflow-(scheduler|worker)" | cut -d "." -f 1 |awk '{print $1}')

#Checking airflow status
if [[ $server_role = "airflow-worker" ]]; then
    command="celery --app airflow.providers.celery.executors.celery_executor.app inspect ping -d celery@${HOSTNAME} | grep -i Worker"
elif [[ $server_role = "airflow-scheduler" ]]; then
    command="curl -i -s -o /dev/null -w %{http_code} http://localhost:8974/health"
else
    echo "No monitored"
fi

while true; do
    readystatus=$($command)
    if [[ "$readystatus" = *"Worker is ready"* || $readystatus -eq 200 ]]; then
        echo "Server OK"
        aws autoscaling set-instance-health --instance-id $instance --health-status Healthy
        sleep 30
    else
        echo "Server Unhealthy"
        echo $readystatus
        aws autoscaling set-instance-health --instance-id $instance --health-status Unhealthy
        sleep 30
    fi

done
