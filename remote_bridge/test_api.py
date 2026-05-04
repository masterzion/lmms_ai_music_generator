import os

SERVER_URL = "http://localhost:8000/generate_pattern"
OUTPUT_FILE = "test_pattern.mid"

def test_generation():
    import requests
    payload = {
        "genre": "Techno",
        "length": 16,
        "energy": 0.8,
        "prompt": "High energy techno loop"
    }
    
    print(f"Sending request to {SERVER_URL}...")
    try:
        response = requests.post(SERVER_URL, json=payload)
        
        if response.status_code == 200:
            print("Success! Saving MIDI file...")
            with open(OUTPUT_FILE, "wb") as f:
                f.write(response.content)
            print(f"MIDI file saved as {OUTPUT_FILE}")
            print(f"File size: {os.path.getsize(OUTPUT_FILE)} bytes")
        else:
            print(f"Failed! Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    # Ensure 'requests' is installed for the test
    try:
        import requests
    except ImportError:
        print("Installing 'requests' for test script...")
        import subprocess
        subprocess.check_call(["pip", "install", "requests"])
        import requests
        
    test_generation()
