(function () {
    let $ctrl = this;

    const launchTraining = (button, trainingType) => {
        button.disabled = true;
        fetch('/training', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                'training_type': trainingType
            })
        })
            .then((response) => {
                if (response.status === 200) {
                    console.log('Training started');
                }
            })
            .catch((error) => {
                // There was an error
                console.warn('Error launching the training:', error);
            })
            .finally(() => {
                button.disabled = false;
            });

    }

    const deleteClient = (button, client__url) => {
        button.disabled = true;
        fetch('/clientun', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                'client_url':client__url
            }) 
            
        })
            .then((response) => {
                if (response.status === 200) {
                    console.log('Client deleted');
                }
            })
            .catch((error) => {
                // There was an error
                console.warn('Error deleting the client:', error);
            })
            .finally(() => {
                button.disabled = false;
            });

    }

   
    const init = () => {
        $ctrl.mnistTrainingButton = document.getElementById('mnistTrainingButton');
        $ctrl.mnistTrainingButton.addEventListener('click', () => {
            launchTraining(this, 'MNIST');
        }, false);


        $ctrl.chestXRayTrainingButton = document.getElementById('chestXRayTrainingButton');
        $ctrl.chestXRayTrainingButton.addEventListener('click', () => {
            launchTraining(this, 'CHEST_X_RAY_PNEUMONIA');
        }, false);

         $ctrl.deleteClientButton = document.getElementById('deleteClientButton');
        $ctrl.deleteClientButton.addEventListener('click', () => {
            deleteClient(this, $ctrl.deleteClientButton.getAttribute('client-url'));
        }, false);
       
    }

    init();
})();
