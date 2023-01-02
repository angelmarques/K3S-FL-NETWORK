#!/bin/bash
# Un script  para actualizar la imagen del deployment del server con la imagen mas reciente del registry
kubectl set image --record deployment.apps/serverdeployment server-01=angelmarques/flnetwork-registry:latest 
