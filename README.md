# JET_GAME

Игра (клиент на python + сервер на C) про воздушные бои в 2D.

Текущее управление:
    !Нужна английская раскладка
    Камера:
        изначально смотрит на (0, 0) координат
        8 - выбрать основного игрока
        9 - выбрать бота-мишень
        U - выбрать последнюю выпущенную ракету

    Основной игрок:
        ускорение/замедление на LShift/LCtrl
        повороты на a/d
        смена вооружения на ~
        управление радаром: 1 - захват/снятие захвата с цели, 2 - выбор цели для захвата, tab - выбор угла сканирования (30, 45, 60 градусов), CAPS LOSK - выбор дальности сканирования (в пикселях), = - вкл/выкл радар
        
    Бот-мишень:
        ускоренине на стрелочки вверх/вниз
        повороты на стрелочки влево/вправо