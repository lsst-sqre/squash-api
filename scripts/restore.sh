#!/bin/bash
namespace=$1
dir=$2

[ -z "$namespace" ] || [ -z "$dir" ] && \
echo "Usage: ./restore.sh <namespace> <input dir>" && exit 1

context=$(kubectl config current-context)

read -p "Using kubectl context $context. Continue [N]?" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo "Looking for the InfluxDB pod"
  pod=$(kubectl get pods -n $namespace | grep influxdb | cut -d " " -f1)
  echo "Found pod $pod in the $namespace namespace."

  echo "Copying files to $pod pod"
  kubectl cp $dir $namespace/$pod:$dir

  echo "Restoring $database database"
  kubectl exec -it -n $namespace $pod -- influxd \
  restore -portable $dir
fi
