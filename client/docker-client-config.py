# Configuration file used for client node when running on Docker
from os import environ

DEFAULT_SERVER_URL = 'http://192.168.86.37:5000'
GLOBAL_TMP_PATH = '/tmp'
#GLOBAL_DATASETS = '../../../datasets'

GLOBAL_TMP_PATH = None
GLOBAL_DATASETS = None # inside there is chest_xray folder
if environ.get('CLIENT_URL') == "http://192.168.86.37:5001":
    print("I'm client 1")
    GLOBAL_TMP_PATH = '/tmp'
    GLOBAL_DATASETS = '/Users/angelmarques/tfg/federated-learning-network/datasets' # inside there is chest_xray folder
if environ.get('CLIENT_URL') == "http://192.168.86.37:5002":
    print("I'm client 2")
    GLOBAL_TMP_PATH = '/tmp2'
    GLOBAL_DATASETS = '/Users/angelmarques/tfg/federated-learning-network/datasets' # inside there is chest_xray folder
if environ.get('CLIENT_URL') == "http://192.168.86.37:5003":
    print("I'm client 3")
    GLOBAL_TMP_PATH = '/tmp3'
    GLOBAL_DATASETS = '/Users/angelmarques/tfg/federated-learning-network/datasets' # inside there is chest_xray folder
if environ.get('CLIENT_URL') == "http://192.168.86.37:5004":
    print("I'm client 4")
    GLOBAL_TMP_PATH = '/tmp4'
    GLOBAL_DATASETS = '/Users/angelmarques/tfg/federated-learning-network/datasets' # inside there is chest_xray folder


GLOBAL_DATASETS = '/Users/angelmarques/tfg/federated-learning-network/datasets'

