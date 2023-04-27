#!/bin/bash
namespace=$1
database=$2

[ -z "$namespace" ] || [ -z "$database" ] && \
echo "Usage: ./dump.sh <namespace> <database>" && exit 1

context=$(kubectl config current-context)

read -p "Using kubectl context $context. Continue [N]?" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
  pod=$(kubectl get pods -n $namespace | grep influxdb | cut -d " " -f1)
  echo "Found pod $pod in the $namespace namespace."
  date=$(date +%Y-%m-%d-%H-%M-%S)

  echo "Dumping $database database"
  kubectl exec -it -n $namespace $pod -- influxd \
  backup -portable -database $database ./$database-$date.influx

  echo "Copying files to $database-$date.influx"
  kubectl cp $namespace/$pod:$database-$date.influx $database-$date.influx

fi
