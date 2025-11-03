"""FSM States для регистрации родителя"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния процесса регистрации родителя"""

    awaiting_email = State()  # Ожидание email ребёнка
    awaiting_code = State()  # Ожидание кода привязки (альтернатива email)
    awaiting_confirmation = State()  # Подтверждение привязки к ученику
