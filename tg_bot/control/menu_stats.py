import time

from locales.localizer import Localizer
from Utils.funpay_time import funpay_now
from tg_bot.constants.sales_stats import STATS_CACHE_SECONDS
from tg_bot.keyboard_views.menu import stats_keyboard
from tg_bot.sales_stats import collect_sales, stats_text, summarize


class MenuStats:
    def menu_stats(self, call, token, argument):
        summary = getattr(self, "sales_stats", None)
        if summary is None or time.time() - summary.made_at >= STATS_CACHE_SECONDS:
            self.menu_refresh_stats(call, token, argument)
            return
        translate = Localizer().translate
        self.menu_render(call, stats_text(summary, translate), stats_keyboard(token))

    def menu_refresh_stats(self, call, token, argument):
        translate = Localizer().translate
        if not self.menu_store.begin_read(token):
            self.menu_render(call, translate("menu_busy"), stats_keyboard(token))
            return
        try:
            self.menu_render(call, translate("menu_stats_loading"), None)
            now = funpay_now()
            orders, complete = collect_sales(self.cardinal.account, now)
            self.sales_stats = summarize(orders, now, complete)
            self.menu_render(
                call, stats_text(self.sales_stats, translate), stats_keyboard(token)
            )
        finally:
            self.menu_store.finish_read(token)
