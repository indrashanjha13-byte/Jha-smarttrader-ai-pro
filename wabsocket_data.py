class MarketFeed:

    def connect(self):

        print(
            "Market Feed Connected"
        )

    def on_tick(
        self,
        data
    ):

        print(data)
