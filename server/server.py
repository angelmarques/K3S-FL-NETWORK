import asyncio
import sys
import aiohttp
import torch
import requests
import random

from kubernetes import client, config

import numpy as np

from .utils import model_params_to_request_params
from .federated_learning_config import FederatedLearningConfig
from .client_training_status import ClientTrainingStatus
from .server_status import ServerStatus
from .training_client import TrainingClient
from .training_type import TrainingType


class Server:
    def __init__(self):
        self.mnist_model_params = None
        self.chest_x_ray_model_params = None
        self.init_params()
        self.training_clients = {}
        self.status = ServerStatus.IDLE
        config.load_incluster_config()
        self.v1 = client.AppsV1Api()

    def init_params(self):
        if self.mnist_model_params is None:
            weights = torch.randn((28 * 28, 1), dtype=torch.float, requires_grad=True)
            bias = torch.randn(1, dtype=torch.float, requires_grad=True)
            self.mnist_model_params = weights, bias

    async def start_training(self, training_type):
        if len(self.training_clients) == 0:
            print("There aren't any clients registered in the system, nothing to do yet, setting Server to IDLE")
            self.status = ServerStatus.IDLE
        elif self.status != ServerStatus.IDLE:
            print('Server is not ready for training yet, status and current clients:', self.status)
            for training_client in self.training_clients.values():
                print(training_client)
        else:
            request_body = {}
            federated_learning_config = None
            if training_type == TrainingType.MNIST:
                request_body = model_params_to_request_params(training_type, self.mnist_model_params)
                federated_learning_config = FederatedLearningConfig(learning_rate=1., epochs=20, batch_size=256)
            elif training_type == TrainingType.CHEST_X_RAY_PNEUMONIA:
                request_body = model_params_to_request_params(training_type, self.chest_x_ray_model_params)
                federated_learning_config = FederatedLearningConfig(learning_rate=0.0001, epochs=1, batch_size=2)

            request_body['learning_rate'] = federated_learning_config.learning_rate
            request_body['epochs'] = federated_learning_config.epochs
            request_body['batch_size'] = federated_learning_config.batch_size
            request_body['training_type'] = training_type
            print('There are', len(self.training_clients), 'clients registered')
            tasks = []
            for training_client in self.training_clients.values():
                tasks.append(asyncio.ensure_future(self.do_training_client_request(training_type, training_client, request_body)))
            print('Requesting training to clients...')
            self.status = ServerStatus.CLIENTS_TRAINING
            await asyncio.gather(*tasks)
        sys.stdout.flush()

    async def do_training_client_request(self, training_type, training_client, request_body):
        request_url = training_client.client_url + '/training'
        print('Requesting training to client', request_url)
        try: 
            async with aiohttp.ClientSession() as session:
                training_client.status = ClientTrainingStatus.TRAINING_REQUESTED
                async with session.post(request_url, json=request_body, timeout=240) as response:
                    if response.status != 200:
                        print('Error requesting training to client', training_client.client_url)
                        training_client.status = ClientTrainingStatus.TRAINING_REQUEST_ERROR
                        self.update_server_model_params(training_type)
                    else:
                        print('Client', training_client.client_url, 'started training')
        except asyncio.TimeoutError:
            print('Agotado el tiempo de entrenamiento del cliente', training_client.client_url)
            print('Se eliminará al cliente', training_client.client_url)
            self.unregister_client(training_client.client_url)
            self.update_server_model_params(training_type)
         


    def update_client_model_params(self, training_type, training_client, client_model_params):
        print('New model params received from client', training_client.client_url)
        training_client.model_params = client_model_params
        training_client.status = ClientTrainingStatus.TRAINING_FINISHED
        self.update_server_model_params(training_type)

    def update_server_model_params(self, training_type):
        if self.can_update_central_model_params():
            print('Updating global model params')
            self.status = ServerStatus.UPDATING_MODEL_PARAMS
            if len (self.training_clients) == 0:
                print ('No clients working, no updates')
                self.status = ServerStatus.IDLE
            elif training_type == TrainingType.MNIST:
                received_weights = []
                received_biases = []
                for training_client in self.training_clients.values():
                    if training_client.status == ClientTrainingStatus.TRAINING_FINISHED:
                        received_weights.append(training_client.model_params[0])
                        received_biases.append(training_client.model_params[1])
                        training_client.status = ClientTrainingStatus.IDLE
                new_weights = torch.stack(received_weights).mean(0)
                new_bias = torch.stack(received_biases).mean(0)
                self.mnist_model_params = new_weights, new_bias
                print('Model weights for', TrainingType.MNIST, 'updated in central model')
            elif training_type == TrainingType.CHEST_X_RAY_PNEUMONIA:
                received_weights = []
                for training_client in self.training_clients.values():
                    if training_client.status == ClientTrainingStatus.TRAINING_FINISHED:
                        training_client.status = ClientTrainingStatus.IDLE
                        received_weights.append(training_client.model_params)
                    elif training_client.status == ClientTrainingStatus.TRAINING_REQUEST_ERROR:
                        training_client.status = ClientTrainingStatus.IDLE
                        print('Putting IDLE status to client as there was error requesting training to client', training_client.client_url)
                if len (received_weights) > 0:
                    #new_weights = np.stack(received_weights).mean(0)# <- last hour edit, works in local but inexplicably not through k3s
                    number=random.randint(0, len(received_weights)-1)
                    self.chest_x_ray_model_params = received_weights[number]
                    #self.chest_x_ray_model_params = new_weights
                    print('Model weights for', TrainingType.CHEST_X_RAY_PNEUMONIA, 'updated in central model')
                else:
                    print('Model weights for', TrainingType.CHEST_X_RAY_PNEUMONIA, 'werent updated in central model as werent received')
            self.status = ServerStatus.IDLE
        sys.stdout.flush()

    def can_update_central_model_params(self):
        for training_client in self.training_clients.values():
            if training_client.status != ClientTrainingStatus.TRAINING_FINISHED \
                    and training_client.status != ClientTrainingStatus.TRAINING_REQUEST_ERROR:
                return False
        return True

    def register_client(self, client_url):
        print('Registering new training client [', client_url, ']')
        if self.training_clients.get(client_url) is None:
            self.training_clients[client_url] = TrainingClient(client_url)
            print('Client [', client_url, '] registered successfully')
        else:
            print('Client [', client_url, '] was already registered in the system')
            self.training_clients.get(client_url).status = ClientTrainingStatus.IDLE
        sys.stdout.flush()

    def delete_deployment(self, api, client_url):
        # Delete deployment
        deploymentname= "no_name"
        #match client_url:
        #    case "http://10.43.130.245:5000":
        #        deploymentname= "client1"
        #    case "http://10.43.29.252:5000":
        #        deploymentname= "client2"
        #    case "http://10.43.138.229:5000":
        #        deploymentname= "client3"
        #    case "http://10.43.216.86:5000":
        #        deploymentname= "client5"
        #    case "http://10.43.159.212:5000":
        #        deploymentname= "client6"

        if client_url == "http://10.43.130.245:5000":
            deploymentname= "client1"
        elif client_url == "http://10.43.29.252:5000":
            deploymentname= "client2"
        elif client_url == "http://10.43.138.229:5000":
            deploymentname= "client3"
        elif client_url == "http://10.43.216.86:5000":
            deploymentname= "client5" 
        elif client_url == "http://10.43.159.212:5000":
            deploymentname= "client6"



        resp = api.delete_namespaced_deployment(
        name=deploymentname,
        namespace="default"
        )
        self.v1 = client.AppsV1Api()
        print("\n[INFO] deployment deleted.")

    def unregister_client(self, client_url):
        print('Unregistering client [', client_url, ']')
        try:
            self.training_clients.pop(client_url)
            self.delete_deployment(self.v1,client_url)
            print('Client [', client_url, '] unregistered successfully')
        except KeyError:
            print('Client [', client_url, '] is not registered yet')
        sys.stdout.flush()

    def can_do_training(self):
        for training_client in self.training_clients.values():
            if training_client.status != ClientTrainingStatus.IDLE \
                    and training_client.status != ClientTrainingStatus.TRAINING_REQUEST_ERROR:
                return False

        return True

