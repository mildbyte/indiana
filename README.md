# indiana
A Telegram treasure hunt bot that generates a random location in Hyde Park. Make a guess by going to a location and sending the location to the bot -- it will reply with the rough distance from the treasure. You can configure the number of guesses you're allowed and the error in the distance that's reported to you.

Note the "treasure" might be in an inaccessible location -- the area where it's generated is just a rectangle. I take no responsibility for you ending up in [the Serpentine](https://en.wikipedia.org/wiki/The_Serpentine).

# Running

  * You'll need to [create a Telegram bot](https://core.telegram.org/bots#6-botfather) and get a bot token as well as a chat reference ID (send a message to the bot and call get_updates to see the ID of the chat between you and the bot).
  * You also need a couple of Python packages like NumPy and requests.
  * Run the bot by doing `indiana.py <bot token> <chat ID>`
  * You can obviously "cheat" by sending the bot a location instead of going there and sending it your physical location.
