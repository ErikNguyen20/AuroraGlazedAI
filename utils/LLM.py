from typing import Optional, List

from tiktoken import get_encoding
from g4f import ChatCompletion, models
from g4f.Provider import (Bard, H2o)  # NON-GPT

# Information about each provider
# https://github.com/xtekky/gpt4free#gpt-35--gpt-4
from g4f.Provider import (Bing, AItianhu, Acytoo, AiAsk, Chatgpt4Online, ChatgptDemo, ChatBase, ChatgptAi, ChatgptLogin, Aivvm, CodeLinkAva, DeepAi,
                          GptGo, Vitalentum, Wewordle, Ylokh, You, Yqcloud)


class LLM:
    TOKEN_COUNT_THRESHOLD = 3900
    RETRY_COUNT = 3  # LLM request max retry count

    def __init__(self):
        self.tokenizer = get_encoding("cl100k_base")
        self.providers = [Bing, AItianhu, Acytoo, AiAsk, Chatgpt4Online, ChatgptDemo, ChatBase, ChatgptAi, ChatgptLogin, Aivvm, CodeLinkAva, DeepAi,
                          GptGo, Vitalentum, Wewordle, Ylokh, You, Yqcloud]

    # async def LLM_get_response(self, all_messages_raw: List[dict]) -> Optional[str]:
    #     try:
    #         response = await g4f.ChatCompletion.create_async(model=g4f.models.default, messages=all_messages_raw)
    #         if self.determine_if_valid_response(response):
    #             return response
    #         else:
    #             raise Exception("Failed Valid Response Check.")
    #     except Exception as e:
    #         print("Error in LLM response, ", str(e))
    #         pass
    #
    #     # Failed to get a response
    #     return None

    async def LLM_get_response(self, all_messages_raw: List[dict]) -> Optional[str]:
        # Iterates over every provider until one of them gets a valid response
        for _ in range(LLM.RETRY_COUNT):
            for provider in self.providers:
                if not provider.working:
                    continue
                try:
                    # Retrieves response from g4f provider
                    response = await ChatCompletion.create_async(model=models.default, messages=all_messages_raw,
                                                                     provider=provider)
                    if self.determine_if_valid_response(response):
                        return response
                except Exception as e:
                    print(f"\tPROVIDER: {provider.__name__} \tERROR: {str(e)}")
                    pass

        # Failed to get a response
        return None

    def determine_if_valid_response(self, response: Optional[str]) -> bool:
        # Determines if the response from the LLM is invalid. This will use heuristic rules.
        if response is None or len(response) == 0 or len(response) > 1980:
            return False
        if response.lower().find("sorry, your app version is outdated.") != -1:
            return False
        if response.lower().find("chatbase") != -1:
            return False

        return True

    # Gets the number of total tokens that a message has
    def compute_messages_token_count(self, all_messages_raw: List[dict]) -> int:
        combined_str = ' '.join(message["content"] for message in all_messages_raw)
        return len(self.tokenizer.encode(combined_str))

