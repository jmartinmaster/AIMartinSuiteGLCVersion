# The Martin Suite (GLC Edition)
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

from modules.utils import ensure_external_directory, external_path, local_or_resource_path, resource_path
from PIL import Image

__module_name__ = "Path Helper Shim"
__version__ = "1.1.4"

__all__ = [
    "resource_path",
    "external_path",
    "local_or_resource_path",
    "ensure_external_directory",
]

def create_test_ico():
    # Create a simple blue image
    size = (64, 64)
    blue_image = Image.new("RGBA", size, "blue")

    # Save as ICO file
    ico_path = "icon.ico"
    blue_image.save(ico_path, format="ICO")
    print(f"Test ICO file created at {ico_path}")

def create_test_png():
    # Create a simple blue image
    size = (64, 64)
    blue_image = Image.new("RGBA", size, "blue")

    # Save as PNG file
    png_path = "icon.png"
    blue_image.save(png_path, format="PNG")
    print(f"Test PNG file created at {png_path}")

if __name__ == "__main__":
    create_test_ico()