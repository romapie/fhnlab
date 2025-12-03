class NotificationManager:
    def __init__(self, notifiers) -> None:
        self.notifiers = notifiers

    def notify_all(self, message: str):
        for n in self.notifiers:
            try:
                n.notify(message)
            except Exception as e:
                print("Notifier failed: ", e)
