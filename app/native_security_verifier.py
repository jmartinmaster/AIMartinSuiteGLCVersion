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
import os
import platform
import shutil
import subprocess

__module_name__ = "Native Security Verifier"
__version__ = "1.0.0"


class NativeSecurityVerifier:
    def get_status(self):
        system_name = platform.system().lower()
        if system_name == "windows":
            return self._get_windows_status()
        if system_name == "linux":
            return self._get_linux_status()
        return {
            "supported": False,
            "available": False,
            "platform": system_name or "unknown",
            "message": "Native security-device verification is only supported on Windows and Linux runtimes.",
        }

    def verify_access(self, prompt_message):
        system_name = platform.system().lower()
        if system_name == "windows":
            return self._verify_windows(prompt_message)
        if system_name == "linux":
            return self._verify_linux(prompt_message)
        return False, "Native security-device verification is not supported on this runtime."

    def _get_windows_status(self):
        command = self._build_windows_status_command()
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        except Exception as exc:
            return {
                "supported": True,
                "available": False,
                "platform": "windows",
                "message": f"Windows native verification probe failed: {exc}",
            }
        status_text = (result.stdout or result.stderr or "").strip()
        available = result.returncode == 0 and "STATUS:Available" in status_text
        if available:
            message = "Windows Hello native verification is available for developer vault challenges."
        elif status_text:
            message = status_text
        else:
            message = "Windows Hello native verification is not available on this device."
        return {
            "supported": True,
            "available": available,
            "platform": "windows",
            "message": message,
        }

    def _verify_windows(self, prompt_message):
        command = self._build_windows_verify_command(prompt_message)
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
        except Exception as exc:
            return False, f"Windows native verification failed to start: {exc}"
        output_text = "\n".join(part.strip() for part in [result.stdout or "", result.stderr or ""] if part.strip())
        if result.returncode == 0 and "RESULT:Verified" in output_text:
            return True, ""
        if "STATUS:" in output_text and "Available" not in output_text:
            return False, "Windows Hello verification is not available on this device."
        if "RESULT:Canceled" in output_text:
            return False, "Native security-device verification was cancelled."
        if output_text:
            return False, output_text
        return False, "Windows Hello verification did not complete successfully."

    def _get_linux_status(self):
        pkexec_path = shutil.which("pkexec")
        graphical_session = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if pkexec_path and graphical_session:
            return {
                "supported": True,
                "available": True,
                "platform": "linux",
                "message": "Native polkit verification is available for developer vault challenges.",
            }
        if pkexec_path:
            return {
                "supported": True,
                "available": False,
                "platform": "linux",
                "message": "pkexec is installed but no graphical desktop session was detected for native verification prompts.",
            }
        return {
            "supported": True,
            "available": False,
            "platform": "linux",
            "message": "pkexec was not found, so native Linux verification prompts are unavailable.",
        }

    def _verify_linux(self, prompt_message):
        _ = prompt_message
        pkexec_path = shutil.which("pkexec")
        if not pkexec_path:
            return False, "pkexec is not installed, so native Linux verification is unavailable."
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return False, "A graphical desktop session is required for native Linux verification prompts."
        try:
            result = subprocess.run([pkexec_path, "/usr/bin/true"], capture_output=True, text=True, timeout=180, check=False)
        except Exception as exc:
            return False, f"Native Linux verification failed to start: {exc}"
        output_text = "\n".join(part.strip() for part in [result.stdout or "", result.stderr or ""] if part.strip())
        if result.returncode == 0:
            return True, ""
        lowered_output = output_text.lower()
        if "dismissed" in lowered_output or "cancel" in lowered_output:
            return False, "Native security-device verification was cancelled."
        if output_text:
            return False, output_text
        return False, "Native Linux verification did not complete successfully."

    def _build_windows_status_command(self):
        script = (
            "& { "
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
            "$type = [Windows.Security.Credentials.UI.UserConsentVerifier, Windows.Security.Credentials.UI, ContentType=WindowsRuntime]; "
            "$op = $type::CheckAvailabilityAsync(); "
            "$extensions = [System.WindowsRuntimeSystemExtensions]; "
            "$asTaskMethod = $extensions.GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -match 'IAsyncOperation' } | Select-Object -First 1; "
            "$genericAsTask = $asTaskMethod.MakeGenericMethod([Windows.Security.Credentials.UI.UserConsentVerifierAvailability]); "
            "$task = $genericAsTask.Invoke($null, @($op)); "
            "while (-not $task.IsCompleted) { Start-Sleep -Milliseconds 50 }; "
            "$availability = $task.Result.ToString(); "
            "Write-Output ('STATUS:' + $availability); "
            "if ($availability -eq 'Available') { exit 0 } else { exit 2 } "
            "}"
        )
        return ["powershell.exe", "-NoProfile", "-Command", script]

    def _build_windows_verify_command(self, prompt_message):
        escaped_prompt = str(prompt_message or "Verify access to continue.").replace("'", "''")
        script = (
            "& { "
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
            "$type = [Windows.Security.Credentials.UI.UserConsentVerifier, Windows.Security.Credentials.UI, ContentType=WindowsRuntime]; "
            "$availabilityOp = $type::CheckAvailabilityAsync(); "
            "$extensions = [System.WindowsRuntimeSystemExtensions]; "
            "$asTaskMethod = $extensions.GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -match 'IAsyncOperation' } | Select-Object -First 1; "
            "$availabilityTaskMethod = $asTaskMethod.MakeGenericMethod([Windows.Security.Credentials.UI.UserConsentVerifierAvailability]); "
            "$availabilityTask = $availabilityTaskMethod.Invoke($null, @($availabilityOp)); "
            "while (-not $availabilityTask.IsCompleted) { Start-Sleep -Milliseconds 50 }; "
            "$availability = $availabilityTask.Result.ToString(); "
            "Write-Output ('STATUS:' + $availability); "
            "if ($availability -ne 'Available') { exit 2 }; "
            f"$verifyOp = $type::RequestVerificationAsync('{escaped_prompt}'); "
            "$verifyTaskMethod = $asTaskMethod.MakeGenericMethod([Windows.Security.Credentials.UI.UserConsentVerificationResult]); "
            "$verifyTask = $verifyTaskMethod.Invoke($null, @($verifyOp)); "
            "while (-not $verifyTask.IsCompleted) { Start-Sleep -Milliseconds 50 }; "
            "$verification = $verifyTask.Result.ToString(); "
            "Write-Output ('RESULT:' + $verification); "
            "if ($verification -eq 'Verified') { exit 0 }; "
            "if ($verification -eq 'Canceled') { exit 1 }; "
            "exit 3 "
            "}"
        )
        return ["powershell.exe", "-NoProfile", "-Command", script]


native_security_verifier = NativeSecurityVerifier()