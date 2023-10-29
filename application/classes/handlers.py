from telegram.ext import BaseHandler, ConversationHandler


class EndHandler(BaseHandler):
    def __init__(self):
        super().__init__(self.callback_end)

    def check_update(self, _) -> bool:
        return True

    @staticmethod
    async def callback_end(_, __):
        return ConversationHandler.END
