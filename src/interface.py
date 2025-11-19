from openai import OpenAI

class Responder():

    def __init__(self, api_key, model: str = "", base: str = ""):
        self._api_key = api_key
        self._base = base
        self.model = model
        if self.model == "":
            self.model = "gpt-5-nano" # Default model for now
        self.client = self._generateClient()

    def _generateClient(self):
        if self._base != "": # Pointing to local ai 
            return OpenAI(api_key=self._api_key, base_url=self._base)
        else: # Pointing to OpenAI
            return OpenAI(api_key=self._api_key)

    def generate_response(self, message: str, instructions: str, images: list = []):
        input = [{
            "role": "user",
            "content": [
                {"type":"input_text", "text":message},
            ]
        }]

        # Add images
        for image in images:
            input[0]["content"].append({"type":"input_image", "image_url":image})

        response = self.client.responses.create(
            model = self.model,
            instructions=instructions,
            input=input
        )
        
        print(response)
        print(len(response.output_text))
        return response.output_text
