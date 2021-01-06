#!/bin/bash
namespace=$1

[ -z "$namespace" ] && \
echo "Usage: ./contextdb.sh <namespace>" && exit 1

context=$(kubectl config current-context)

read -p "Using kubectl context $context. Continue [N]?" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
  pod=$(kubectl get pods -n $namespace | grep chronograf | cut -d " " -f1)

  if [ ! -z "$pod" ]
  then
    echo "Found pod $pod in the $namespace namespace."
    echo "Copying Chronograf context database"

    kubectl cp $namespace/$pod:var/lib/chronograf/chronograf-v1.db chronograf-v1.db
  fi

  pod=$(kubectl get pods -n $namespace | grep kapacitor | cut -d " " -f1)

  if [ ! -z "$pod" ]
  then
    echo "Found pod $pod in the $namespace namespace."
    echo "Copying Kapacitor context database"

    kubectl cp $namespace/$pod:var/lib/kapacitor/kapacitor.db kapacitor.db
  fi
fi
