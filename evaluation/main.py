import os
import base64
import requests


# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')


# Directory name
image_directory = "NotAbuse"


api_key = "" //Add your key here
total_images = 0
no_count = 0

# Iterate through each file in the directory
for filename in os.listdir(image_directory):
  total_images += 1
  if filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(
          ".jpeg"):
    image_path = os.path.join(image_directory, filename)
    base64_image = encode_image(image_path)

    headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {api_key}"
    }

    payload = {
      "model": "gpt-4o",
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "We define 'proxy animal abuse' as any violent behavior (or behavior that would cause stress) "
                      "towards any animals present in the image. Does this image depict animal abuse? Would you say "
                      "that some harm has occurred in the past, is currently occurring, or is about to occur to any"
                      " creature present in the image? Please answer with just yes or no."

            },
            {
              "type": "image_url",
              "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
              }
            }
          ]
        }
      ],
      "max_tokens": 300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    # Extract and print the "yes" or "no" response from the JSON
    response_json = response.json()
    answer = response_json['choices'][0]['message']['content'].strip()  # Adjust based on actual response structure
    print(f"Response for {filename}: {answer}")
    if answer.lower() == "no":
      no_count += 1


print(f"# no: {no_count}/{total_images} images processed")
