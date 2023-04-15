Plugin: chatai
===
Introducing the "OpenAI Chat Plugin"! With this plugin, you can easily interact with all of OpenAI's chat-based models, including the powerful GPT-3.5-Turbo model.(using 
[openai-python](https://github.com/openai/openai-python)).

## Commands

### chatai
Usage: `aichat`  
Toggle openai chat model interactions of all following messages mentioning the bots username within the room .  

Examples:
* Enable openai GPT model using default values (or disable active model):  
`aichat`
* Enable openai "gpt-3.5-turbo" model:  
`aichat gpt-3.5-turbo`
* Set an individual [system role message content](https://platform.openai.com/docs/guides/chat/introduction) for the room. This string is formatted, the placeholder "{bot_user_id}" will automatically be replaced by bots username:  
`aichat-set-system-role <some example system role message content>`
* Reset to the default [system role message content](https://platform.openai.com/docs/guides/chat/introduction):  
`aichat-set-system-role`
* Respond with the currently configured [system role message content](https://platform.openai.com/docs/guides/chat/introduction) for this room:  
`aichat-print-system-role`

## Configuration
Sensible defaults can be provided in `aichat.yaml`:  
- `allowed_rooms`: List of room-id the plugin is allowed to work in (if empty, all rooms are allowed)  
- `min_power_level`: minimum power level to activate the aichat or change the system role messages content (default: 50)
- `max_tokens`: maximum number of [tokens](https://platform.openai.com/docs/introduction/tokens) that could be spent per request
- `default_model`: The openai API is powered by a set of models with different capabilities and price points. GPT-4 is their latest and most powerful model (limited beta). GPT-3.5-Turbo is the model that powers ChatGPT and is optimized for the best chat experience.
- `default_system_role_content`: The [system role message content](https://platform.openai.com/docs/guides/chat/introduction) used by default. This string is formatted, the placeholder "{bot_user_id}" will automatically be replaced by bots username

## External Requirements
- [openai-python](https://github.com/openai/openai-python) for language detection and the actual translation
