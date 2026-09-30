log_greeting_changed = (
    "$MAGENTA@{} (ID: {})$RESET изменил текст приветствия на $YELLOW{}$RESET."
)
log_greeting_cooldown_changed = "$MAGENTA@{} (ID: {})$RESET изменил интервал приветсвенного сообщения на $YELLOW{}$RESET дн."
log_order_confirm_changed = "$MAGENTA@{} (ID: {})$RESET изменил текст ответа на подтверждение заказа на $YELLOW{}$RESET."
log_review_reply_changed = "$MAGENTA@{} (ID: {})$RESET изменил текст ответа на отзыв с {} зв. на $YELLOW{}$RESET."
log_param_changed = "$MAGENTA@{} (ID: {})$RESET изменил параметр $CYAN{}$RESET секции $YELLOW[{}]$RESET на $YELLOW{}$RESET."
log_notification_switched = "$MAGENTA@{} (ID: {})$RESET переключил уведомления $YELLOW{}$RESET для чата $YELLOW{}$RESET на $CYAN{}$RESET."
log_ad_linked = (
    "$MAGENTA@{} (ID: {})$RESET привязал авто-выдачу к лоту $YELLOW{}$RESET."
)
log_ad_text_changed = '$MAGENTA@{} (ID: {})$RESET изменил текст выдачи лота $YELLOW{}$RESET на $YELLOW"{}"$RESET.'
log_ad_deleted = "$MAGENTA@{} (ID: {})$RESET удалил авто-выдачу лота $YELLOW{}$RESET."
log_gf_created = (
    "$MAGENTA@{} (ID: {})$RESET создал товарный файл $YELLOWstorage/products/{}$RESET."
)
log_gf_unlinked = (
    "$MAGENTA@{} (ID: {})$RESET отвязал товарный файл от лота $YELLOW{}$RESET."
)
log_gf_linked = "$MAGENTA@{} (ID: {})$RESET привязал товарный файл $YELLOWstorage/products/{}$RESET к лоту $YELLOW{}$RESET."
log_gf_created_and_linked = "$MAGENTA@{} (ID: {})$RESET создал и привязал товарный файл $YELLOWstorage/products/{}$RESET к лоту $YELLOW{}$RESET."
log_gf_new_goods = "User {} ({}) added {} products to storage/products/{}."
log_gf_downloaded = "$MAGENTA@{} (ID: {})$RESET запросил товарный файл $YELLOWstorage/products/{}$RESET."
log_gf_deleted = (
    "$MAGENTA@{} (ID: {})$RESET удалил товарный файл $YELLOWstorage/products/{}$RESET."
)
log_ar_added = "$MAGENTA@{} (ID: {})$RESET добавил новую команду $YELLOW{}$RESET."
log_ar_response_text_changed = '$MAGENTA@{} (ID: {})$RESET изменил текст ответа команды $YELLOW{}$RESET на $YELLOW"{}"$RESET.'
log_ar_notification_text_changed = '$MAGENTA@{} (ID: {})$RESET изменил текст уведомления команды $YELLOW{}$RESET на $YELLOW"{}"$RESET.'
log_ar_cmd_deleted = "$MAGENTA@{} (ID: {})$RESET удалил команду $YELLOW{}$RESET."
log_cfg_downloaded = "$MAGENTA@{} (ID: {})$RESET запросил конфиг $YELLOW{}$RESET."
log_tmplt_added = '$MAGENTA@{} (ID: {})$RESET добавил шаблон ответа $YELLOW"{}"$RESET.'
log_tmplt_deleted = '$MAGENTA@{} (ID: {})$RESET удалил шаблон ответа $YELLOW"{}"$RESET.'
log_pl_activated = '$MAGENTA@{} (ID: {})$RESET активировал плагин $YELLOW"{}"$RESET.'
log_pl_deactivated = (
    '$MAGENTA@{} (ID: {})$RESET деактивировал плагин $YELLOW"{}"$RESET.'
)
log_pl_deleted = '$MAGENTA@{} (ID: {})$RESET удалил плагин $YELLOW"{}"$RESET.'
log_pl_delete_handler_err = (
    'Произошла ошибка при выполнении хэндлера удаления плагина $YELLOW"{}"$RESET.'
)
log_new_msg = (
    "$MAGENTA$RESET Новое сообщение в переписке с пользователем $YELLOW{} (CID: {}):"
)
log_sending_greetings = "Пользователь $YELLOW{} (CID: {})$RESET написал впервые! Отправляю приветственное сообщение..."
log_new_cmd = (
    "Получена команда $YELLOW{}$RESET в чате с пользователем $YELLOW{} (CID: {})$RESET."
)
ntfc_new_order = "🧾 <b>Новый заказ</b>\n{}\n\nПокупатель: {}\nСумма: {}\nЗаказ: <code>#{}</code>\n\n{}"
ntfc_new_order_not_in_cfg = "📦 Нужна ручная выдача: лот не подключён к автовыдаче."
ntfc_new_order_ad_disabled = (
    "📦 Нужна ручная выдача: автовыдача выключена в функциях бота."
)
ntfc_new_order_ad_disabled_for_lot = (
    "📦 Нужна ручная выдача: у этого лота автовыдача выключена."
)
ntfc_new_order_user_blocked = (
    "🚫 Товар не выдаётся автоматически: покупатель в чёрном списке."
)
ntfc_new_order_will_be_delivered = "📦 Заказ ожидает автовыдачи."
ntfc_new_review = "⭐ <b>Отзыв покупателя · {}</b>\nЗаказ: <code>{}</code>\n\n<b>Текст отзыва</b>\n<code>{}</code>{}"
ntfc_review_reply_text = "\n\n<b>Ваш ответ</b>\n<code>{}</code>"
crd_proxy_detected = "Обнаружен прокси."
crd_checking_proxy = "Выполняю проверку прокси..."
crd_proxy_err = "Не удалось подключиться к прокси. Убедитесь, что данные введены верно."
crd_proxy_success = "Прокси проверен! IP-адрес: $YELLOW{}$RESET."
crd_acc_get_timeout_err = (
    "Не удалось загрузить данные об аккаунте: превышен тайм-аут ожидания."
)
crd_acc_get_unexpected_err = (
    "Произошла непредвиденная ошибка при получении данных аккаунта."
)
crd_try_again_in_n_secs = "Повторю попытку через {} секунд(-у/-ы)..."
crd_getting_profile_data = "Получаю данные о лотах и категориях..."
crd_profile_get_timeout_err = (
    "Не удалось загрузить данные о лотах аккаунта: превышен тайм-аут ожидания."
)
crd_profile_get_unexpected_err = (
    "Произошла непредвиденная ошибка при получении данных о лотах и категориях."
)
crd_profile_get_too_many_attempts_err = "Произошло ошибка при получении данных о лотах и категориях: превышено кол-во попыток ({})."
crd_profile_updated = "Обновил информацию о лотах $YELLOW({})$RESET и категориях $YELLOW({})$RESET профиля."
crd_tg_profile_updated = "Обновил информацию о лотах $YELLOW({})$RESET и категориях $YELLOW({})$RESET профиля (TG ПУ)."
crd_raise_time_err = 'Не удалось поднять лоты категории $CYAN"{}"$RESET. FunPay говорит: "{}". Следующая попытка через {}.'
crd_raise_unexpected_err = 'Произошла непредвиденная ошибка при попытке поднять лоты категории $CYAN"{}"$RESET. Пауза на 10 секунд...'
crd_raise_status_code_err = (
    'Ошибка {} при поднятии лотов категории $CYAN"{}"$RESET. Пауза на 1 мин...'
)
crd_lots_raised = 'Все лоты категории $CYAN"{}"$RESET подняты!'
crd_raise_wait_3600 = "Следующая попытка через {}."
crd_msg_send_err = "Произошла ошибка при отправке сообщения в чат $YELLOW{}$RESET."
crd_msg_attempts_left = "Осталось попыток: $YELLOW{}$RESET."
crd_msg_no_more_attempts_err = (
    "Не удалось отправить сообщение в чат $YELLOW{}$RESET: превышено кол-во попыток."
)
crd_msg_sent = "Отправил сообщение в чат $YELLOW{}."
crd_session_timeout_err = "Не удалось обновить сессию: превышен тайм-аут ожидания."
crd_session_unexpected_err = "Произошла непредвиденная ошибка при обновлении сессии."
crd_session_no_more_attempts_err = (
    "Не удалось обновить сессию: превышено кол-во попыток."
)
crd_session_updated = "Сессия обновлена."
crd_raise_loop_started = "$CYANЦикл автоподнятия лотов запущен (это не значит, что автоподнятие лотов включено)."
crd_raise_loop_not_started = (
    "$CYANЦикл автоподнятия не был запущен, т.к. на аккаунте не обнаружен лотов."
)
crd_session_loop_started = "$CYANЦикл обновления сессии запущен."
crd_no_plugins_folder = "Папка с плагинами не обнаружена."
crd_no_plugins = "Плагины не обнаружены."
crd_plugin_load_err = "Не удалось загрузить плагин {}."
crd_plugin_handlers_err = (
    "Не удалось зарегистрировать хэндлеры плагина {}. Плагин отключен."
)
crd_invalid_uuid = "Не удалось загрузить плагин {}: невалидный UUID."
crd_uuid_already_registered = "UUID {} ({}) уже зарегистрирован."
crd_handlers_registered = "Хэндлеры из $YELLOW{}.py$RESET зарегистрированы."
crd_handler_err = "Произошла ошибка при выполнении хэндлера."
crd_tg_au_err = "Не удалось изменить сообщение с информацией о пользователе: {}. Попробую без ссылки."
