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
from app.views.production_log_view import ProductionLogView

__module_name__ = "Production Log View Factory"
__version__ = "1.1.0"

def create_production_log_view(parent, dispatcher, controller, model):
    _ = dispatcher
    controller.requested_view_backend = "tk"
    controller.resolved_view_backend = "tk"
    controller.view_backend_fallback_reason = None
    controller.view_backend_fallback_code = None
    return ProductionLogView(parent, dispatcher, controller, model)
