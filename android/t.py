from fastapi import FastAPI
import requests
import ml.py


app = FastAPI()

@app.get('/get_data')
async def get_data():
    source_url = 'https://github.com/SofiaLimorenko/android'
    response = requests.get(source_url)

    if response.status_code == 200:
        data = response.json()
        coordinates = data.get('coordinates')
        wheelchair = data.get('wheelchair')
        time = data.get('time')

        destination_url = ''
        payload = {
            'coordinates': coordinates,
            'wheelchair': wheelchair,
            'time': time
        }

        response = requests.post(destination_url, json=payload)

        if response.status_code == 200:
            return {'message': 'Data sent successfully'}
        else:
            return {'message': 'Failed to send data to the destination repository'}

    else:
        return {'message': 'Failed to retrieve data from the source repository'}