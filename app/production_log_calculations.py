# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from app.controllers.production_log_calculations_controller import ProductionLogCalculationsController
from app.controllers.production_log_calculations_qt_controller import ProductionLogCalculationsQtController

__module_name__ = "Production Log Calculations"
__version__ = "1.1.0"


def get_ui(parent, dispatcher):
    should_use_qt_in_viewport = getattr(dispatcher, "should_use_qt_in_viewport", None)
    if callable(should_use_qt_in_viewport) and should_use_qt_in_viewport("production_log_calculations"):
        return ProductionLogCalculationsQtController(parent=parent, dispatcher=dispatcher)
    return ProductionLogCalculationsController(parent, dispatcher)