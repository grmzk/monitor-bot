MESSAGE_MAX_SIZE = 4096

# ConversationHandler states
FAMILY, NAME, SURNAME, PHONE, DEPARTMENT = range(5)
SHOW = range(1)

# Notification levels
NO_NOTIFICATION = 0
OWN_PATIENTS = 1
OWN_REANIMATION_HOLE = 2
ALL_REANIMATION_HOLE = 3
ALL_NOTIFICATIONS = 4
VASCULAR_CENTER = 5
THERAPY_AND_CARDIOLOGY2 = 6

NOTIFICATION_TITLES = {
    OWN_PATIENTS: 'Пациенты своего отделения',
    OWN_REANIMATION_HOLE: 'Реанимационные залы своего отделения',
    ALL_REANIMATION_HOLE: 'Все реанимационные залы',
    VASCULAR_CENTER: 'Пациенты сосудистого центра',
    THERAPY_AND_CARDIOLOGY2: 'Терапия + 2-я Кардиология',
    ALL_NOTIFICATIONS: 'Уведомления о всех пациентах',
    NO_NOTIFICATION: 'Отключить все уведомления'
}

NOTIFICATION_DESCRIPTIONS = {
    NO_NOTIFICATION: 'не будут приходить никакие уведомления',
    OWN_PATIENTS: 'будут приходить уведомления о всех поступающих '
                  'за вашим отделением пациентах, включая реанимационные залы',
    OWN_REANIMATION_HOLE: 'будут приходить уведомления только '
                          'о реанимационных залах вашего отделения',
    ALL_REANIMATION_HOLE: 'будут приходить уведомления '
                          'о реанимационных залах всех отделений',
    VASCULAR_CENTER: 'будут приходить уведомления о пациентах, '
                     'поступающих за неврологическим '
                     'и кардиологическим отделениями',
    THERAPY_AND_CARDIOLOGY2: 'будут приходить уведомления о пациентах, '
                             'поступающих за отделениями: '
                             '1-я терапия, 2-я терапия и 2-я кардиология',
    ALL_NOTIFICATIONS: 'будут приходить уведомления о всех '
                       'поступающих пациентах во все отделения'
}

STATUS_INPATIENT = 7
STATUS_OUTPATIENT_MAIN = 8
STATUS_OTHER_HOSPITAL = 9
STATUS_PROCESSING = 10

STATUS_OUTPATIENT = 1
STATUS_OVER_DIAGNOSIS = 2
STATUS_DIS_DIAGNOSIS = 3
STATUS_UNREASON_DIRECTED = 4
STATUS_SELF_DENIAL = 5
STATUS_UNREASON_DENY = 6
STATUS_SELF_LEAVE = 188

STATUSES = {
    STATUS_INPATIENT: 'ГОСПИТАЛИЗАЦИЯ',
    STATUS_OUTPATIENT_MAIN: 'АМБУЛАТОРНОЕ ЛЕЧЕНИЕ',
    STATUS_OTHER_HOSPITAL: 'НАПРАВЛЕН В ДРУГОЙ СТАЦИОНАР',
    STATUS_PROCESSING: 'ОБСЛЕДУЕТСЯ'
}

REJECTIONS = {
    STATUS_OUTPATIENT: 'АМБУЛАТОРНОЕ ЛЕЧЕНИЕ',
    STATUS_OVER_DIAGNOSIS: 'ГИПЕРДИАГНОСТИКА',
    STATUS_DIS_DIAGNOSIS: 'РАСХОЖДЕНИЕ ДИАГНОЗА',
    STATUS_UNREASON_DIRECTED: 'НЕОБОСНОВАННО НАПРАВЛЕН',
    STATUS_SELF_DENIAL: 'САМООТКАЗ',
    STATUS_UNREASON_DENY: 'НЕОБОСНОВАННЫЙ ОТКАЗ',
    STATUS_SELF_LEAVE: 'САМОУХОД'
}
