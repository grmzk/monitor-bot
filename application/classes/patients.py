import re
from dataclasses import dataclass
from datetime import datetime

from classes.users import User
from constants import (REJECTIONS, STATUS_INPATIENT, STATUS_OUTPATIENT_MAIN,
                       STATUS_PROCESSING, STATUSES)


@dataclass
class Patient:
    patient_id: int
    card_id: int
    admission_date: datetime
    admission_outcome_date: datetime
    family: str
    name: str
    surname: str
    birthday: datetime
    gender: str
    department: str
    reanimation: str
    incoming_diagnosis: str
    admission_diagnosis: str
    status: int
    reject: int
    inpatient_department: str
    doctor: str

    @staticmethod
    def get_date(date: datetime) -> str:
        return date.strftime('%d.%m.%Y %H:%M')

    def get_admission_date(self) -> str:
        return self.get_date(self.admission_date)

    def get_admission_outcome_date(self) -> str:
        return self.get_date(self.admission_outcome_date)

    def get_full_name(self) -> str:
        return f'{self.family} {self.name} {self.surname}'

    def get_birthday(self) -> str:
        return self.birthday.strftime('%d.%m.%Y')

    def get_age(self) -> str:
        birthday = self.birthday
        now = datetime.now()
        age = (now.year - birthday.year
               - ((now.month, now.day) < (birthday.month, birthday.day)))
        ending: str
        if 5 <= age <= 20:
            ending = 'лет'
        elif age % 10 == 1:
            ending = 'год'
        elif 2 <= age % 10 <= 4:
            ending = 'года'
        else:
            ending = 'лет'
        return f'{age} {ending}'

    def is_reanimation(self) -> bool:
        if self.reanimation == 'F':
            return False
        return True

    def is_outcome(self) -> bool:
        return self.status != STATUS_PROCESSING

    def is_own(self, user: User) -> bool:
        pattern_surgery = re.compile(r'^.* ХИРУРГИЯ$')
        pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
        return ((user.department == self.department)
                or (pattern_surgery.match(self.department)
                    and pattern_surgery.match(user.department))
                or (pattern_therapy.match(self.department)
                    and pattern_therapy.match(user.department)))

    def is_vascular_center(self) -> bool:
        return (self.department == 'КАРДИОЛОГИЯ'
                or self.department == 'НЕВРОЛОГИЯ')

    def is_therapy_or_cardiology2(self) -> bool:
        pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
        return (self.department == '2 Кардиология'
                or pattern_therapy.match(self.department))

    def is_inpatient_own(self, user: User) -> bool:
        pattern_surgery = re.compile(r'^.* ХИРУРГИЯ$')
        pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
        return ((user.department == self.inpatient_department)
                or (pattern_surgery.match(str(self.inpatient_department))
                    and pattern_surgery.match(user.department))
                or (pattern_therapy.match(str(self.inpatient_department))
                    and pattern_therapy.match(user.department)))

    def is_inpatient(self) -> bool:
        return bool(self.inpatient_department)


class PatientInfo:
    def __init__(self, patient: Patient):
        if patient.is_reanimation():
            self.reanimation_hole = '<u>[РЕАНИМАЦИОННЫЙ ЗАЛ]</u>\n'
        else:
            self.reanimation_hole = ''
        self.admission_date = (
            f'<u>Дата поступления:</u> {patient.get_admission_date()}\n'
        )
        if patient.is_outcome():
            self.admission_outcome_date = (
                '<u>Дата исхода:</u> '
                f'{patient.get_admission_outcome_date()}\n'
            )
        else:
            self.admission_outcome_date = ''
        self.department = f'<u>Отделение:</u> {patient.department.upper()}\n'
        if not patient.get_full_name().strip():
            if patient.gender == 'М':
                self.full_name = '<u>Ф.И.О.:</u> НЕИЗВЕСТНЫЙ\n'
            else:
                self.full_name = '<u>Ф.И.О.:</u> НЕИЗВЕСТНАЯ\n'
        else:
            self.full_name = (
                '<u>Ф.И.О.:</u> '
                f'{patient.get_full_name()}\n'
            )
        self.birthday = (
            '<u>Дата рождения:</u> '
            f'{patient.get_birthday()} [{patient.get_age()}]\n'
        )
        self.incoming_diagnosis = (
            '<u>Диагноз при поступлении:</u>\n'
            f'{patient.incoming_diagnosis}\n'
        )
        if patient.admission_diagnosis:
            self.admission_diagnosis = (
                '<u>Диагноз приёмного отделения:</u>\n'
                f'{patient.admission_diagnosis}\n'
            )
        else:
            self.admission_diagnosis = ''
        self.result = '<u>Исход:</u> '
        if patient.status == STATUS_OUTPATIENT_MAIN:
            self.result += REJECTIONS.get(patient.reject,
                                          f'reject={patient.reject}')
        elif patient.status == STATUS_INPATIENT:
            self.result += ('ГОСПИТАЛИЗАЦИЯ '
                            f'[{patient.inpatient_department.upper()}]')
        else:
            self.result += STATUSES.get(patient.status,
                                        f'status={patient.status}')
        self.result += '\n'
        if patient.doctor:
            self.doctor = f'<u>Врач:</u> {patient.doctor}\n'
        else:
            self.doctor = ''

    def get_full_info(self) -> str:
        return (
            '===========================\n'
            f'{self.reanimation_hole}'
            f'{self.admission_date}'
            f'{self.admission_outcome_date}'
            f'{self.department}'
            f'{self.full_name}'
            f'{self.birthday}'
            f'{self.incoming_diagnosis}'
            f'{self.admission_diagnosis}'
            f'{self.result}'
            f'{self.doctor}'
        )

    def get_admission_info(self) -> str:
        return (
            '===========================\n'
            f'{self.reanimation_hole}'
            f'{self.admission_date}'
            f'{self.department}'
            f'{self.full_name}'
            f'{self.birthday}'
            f'{self.incoming_diagnosis}'
        )

    def get_history_info(self) -> str:
        return (
            '===========================\n'
            f'{self.reanimation_hole}'
            f'{self.admission_date}'
            f'{self.department}'
            f'{self.admission_diagnosis or self.incoming_diagnosis}'
            f'{self.result}'
            f'{self.doctor}'
        )
