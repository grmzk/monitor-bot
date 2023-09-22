# Notification levels
NO_NOTIFICATION = 0
OWN_PATIENTS = 1
OWN_REANIMATION_HOLE = 2
ALL_REANIMATION_HOLE = 3
ALL_NOTIFICATIONS = 4

NOTIFICATION_LEVELS = {
    NO_NOTIFICATION: 'Отключить все уведомления',
    OWN_PATIENTS: 'Пациенты своего отделения',
    OWN_REANIMATION_HOLE: 'Реанимационные залы своего отделения',
    ALL_REANIMATION_HOLE: 'Все реанимационные залы',
    ALL_NOTIFICATIONS: 'Уведомления обо всех пациентах'
}

STATUSES = {
    7: 'ГОСПИТАЛИЗАЦИЯ',
    8: 'АМБУЛАТОРНОЕ ЛЕЧЕНИЕ',
    9: 'НАПРАВЛЕН В ДРУГОЙ СТАЦИОНАР',
    10: 'ОБСЛЕДУЕТСЯ'
}

REJECTIONS = {
    1: 'АМБУЛАТОРНОЕ ЛЕЧЕНИЕ',
    2: 'ГИПЕРДИАГНОСТИКА',
    3: 'РАСХОЖДЕНИЕ ДИАГНОЗА',
    4: 'НЕОБОСНОВАННО НАПРАВЛЕН',
    5: 'САМООТКАЗ',
    6: 'НЕОБОСНОВАННЫЙ ОТКАЗ',
    188: 'САМОУХОД'
}
