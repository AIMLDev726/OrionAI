"""
CLI Image Display utilities
===========================

Display images and plots in the CLI using ASCII art, text representations, and other terminal-friendly methods.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple, List
import tempfile

# Optional imports for image processing
try:
    import PIL.Image as PILImage
    from PIL import ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

console = Console()


class CLIImageDisplay:
    """CLI-based image display system."""
    
    def __init__(self):
        self.ascii_chars = "@%#*+=-:. "  # Characters for ASCII art, darkest to lightest
        self.width = 80  # Default ASCII art width
        
    def display_image_info(self, image_path: str) -> bool:
        """Display basic image information."""
        try:
            path = Path(image_path)
            if not path.exists():
                console.print(f"[red]❌ Image not found: {image_path}[/red]")
                return False
            
            # Basic file info
            info_table = Table(title=f"📷 Image: {path.name}", box=box.ROUNDED)
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="white")
            
            info_table.add_row("File Path", str(path))
            info_table.add_row("File Size", f"{path.stat().st_size / 1024:.1f} KB")
            info_table.add_row("File Extension", path.suffix)
            
            if PILLOW_AVAILABLE:
                try:
                    with PILImage.open(path) as img:
                        info_table.add_row("Dimensions", f"{img.width} x {img.height}")
                        info_table.add_row("Format", img.format or "Unknown")
                        info_table.add_row("Mode", img.mode or "Unknown")
                        
                        # Color palette info for smaller images
                        if img.width * img.height < 100000:  # Less than 100k pixels
                            colors = img.getcolors(maxcolors=10)
                            if colors:
                                top_color = max(colors, key=lambda x: x[0])
                                info_table.add_row("Dominant Color", f"RGB{top_color[1]}" if len(top_color[1]) >= 3 else str(top_color[1]))
                except Exception as e:
                    info_table.add_row("Image Info", f"Error: {e}")
            else:
                info_table.add_row("Details", "Install Pillow for detailed info")
            
            console.print(info_table)
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error displaying image info: {e}[/red]")
            return False
    
    def display_as_ascii(self, image_path: str, width: Optional[int] = None) -> bool:
        """Convert and display image as ASCII art."""
        if not PILLOW_AVAILABLE:
            console.print("[red]❌ Pillow required for ASCII art display[/red]")
            console.print("Install with: pip install Pillow")
            return False
        
        try:
            width = width or self.width
            
            with PILImage.open(image_path) as img:
                # Convert to grayscale
                img = img.convert('L')
                
                # Calculate height to maintain aspect ratio
                aspect_ratio = img.height / img.width
                height = int(width * aspect_ratio * 0.55)  # 0.55 to account for character height
                
                # Resize image
                img = img.resize((width, height))
                
                # Convert to ASCII
                ascii_lines = []
                for y in range(height):
                    line = ""
                    for x in range(width):
                        pixel = img.getpixel((x, y))
                        # Map pixel value (0-255) to ASCII character index
                        char_index = min(len(self.ascii_chars) - 1, pixel // (256 // len(self.ascii_chars)))
                        line += self.ascii_chars[char_index]
                    ascii_lines.append(line)
                
                # Display ASCII art
                ascii_text = "\\n".join(ascii_lines)
                
                console.print(Panel(
                    ascii_text,
                    title=f"🎨 ASCII Art: {Path(image_path).name}",
                    border_style="green",
                    width=width + 4
                ))
                
                return True
                
        except Exception as e:
            console.print(f"[red]❌ Error creating ASCII art: {e}[/red]")
            return False
    
    def display_color_blocks(self, image_path: str, block_size: int = 2) -> bool:
        """Display image using colored Unicode blocks."""
        if not PILLOW_AVAILABLE:
            console.print("[red]❌ Pillow required for color block display[/red]")
            return False
        
        try:
            with PILImage.open(image_path) as img:
                # Convert to RGB
                img = img.convert('RGB')
                
                # Resize to reasonable size
                max_width = 40
                aspect_ratio = img.height / img.width
                width = min(max_width, img.width // block_size)
                height = int(width * aspect_ratio)
                
                img = img.resize((width, height))
                
                # Create colored output
                lines = []
                for y in range(height):
                    line = Text()
                    for x in range(width):
                        r, g, b = img.getpixel((x, y))
                        # Use Unicode block character with color
                        line.append("██", style=f"rgb({r},{g},{b})")
                    lines.append(line)
                
                # Display
                console.print(Panel(
                    "\\n".join([str(line) for line in lines]),
                    title=f"🌈 Color Blocks: {Path(image_path).name}",
                    border_style="blue"
                ))
                
                return True
                
        except Exception as e:
            console.print(f"[red]❌ Error creating color blocks: {e}[/red]")
            return False
    
    def display_histogram(self, image_path: str) -> bool:
        """Display image color histogram."""
        if not PILLOW_AVAILABLE:
            console.print("[red]❌ Pillow required for histogram[/red]")
            return False
        
        try:
            with PILImage.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get histograms for each channel
                r_hist = img.histogram()[0:256]    # Red
                g_hist = img.histogram()[256:512]  # Green  
                b_hist = img.histogram()[512:768]  # Blue
                
                # Create simple text histogram
                hist_table = Table(title=f"📊 Color Histogram: {Path(image_path).name}", box=box.ROUNDED)
                hist_table.add_column("Range", style="cyan")
                hist_table.add_column("Red", style="red")
                hist_table.add_column("Green", style="green")
                hist_table.add_column("Blue", style="blue")
                
                # Group into ranges
                ranges = [(0, 64), (64, 128), (128, 192), (192, 256)]
                
                for start, end in ranges:
                    r_sum = sum(r_hist[start:end])
                    g_sum = sum(g_hist[start:end])
                    b_sum = sum(b_hist[start:end])
                    
                    # Simple bar representation
                    max_sum = max(r_sum, g_sum, b_sum)
                    if max_sum > 0:
                        r_bar = "█" * min(20, int(20 * r_sum / max_sum))
                        g_bar = "█" * min(20, int(20 * g_sum / max_sum))
                        b_bar = "█" * min(20, int(20 * b_sum / max_sum))
                    else:
                        r_bar = g_bar = b_bar = ""
                    
                    hist_table.add_row(
                        f"{start}-{end-1}",
                        f"{r_bar} ({r_sum:,})",
                        f"{g_bar} ({g_sum:,})",
                        f"{b_bar} ({b_sum:,})"
                    )
                
                console.print(hist_table)
                return True
                
        except Exception as e:
            console.print(f"[red]❌ Error creating histogram: {e}[/red]")
            return False
    
    def display_plot_data(self, image_path: str) -> bool:
        """Extract and display plot data if it's a matplotlib plot."""
        try:
            # This is a simplified version - in practice, you'd need to 
            # analyze the plot to extract data
            console.print(Panel(
                f"📈 Plot file: {Path(image_path).name}\\n"
                f"📂 Location: {image_path}\\n"
                f"💡 This appears to be a generated plot.\\n"
                f"🔍 Use the ASCII or color block display options to view it in the terminal.",
                title="📊 Plot Information",
                border_style="yellow"
            ))
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error analyzing plot: {e}[/red]")
            return False
    
    def display_image_cli(self, image_path: str, method: str = "auto") -> bool:
        """
        Display image in CLI using specified method.
        
        Args:
            image_path: Path to image file
            method: Display method ("auto", "info", "ascii", "blocks", "histogram")
        
        Returns:
            True if successful
        """
        if not Path(image_path).exists():
            console.print(f"[red]❌ Image not found: {image_path}[/red]")
            return False
        
        if method == "auto":
            # Auto-select best method based on image
            if PILLOW_AVAILABLE:
                try:
                    with PILImage.open(image_path) as img:
                        if img.width * img.height < 10000:  # Small image
                            method = "blocks"
                        else:
                            method = "ascii"
                except:
                    method = "info"
            else:
                method = "info"
        
        success = False
        
        if method == "info":
            success = self.display_image_info(image_path)
        elif method == "ascii":
            success = self.display_as_ascii(image_path)
        elif method == "blocks":
            success = self.display_color_blocks(image_path)
        elif method == "histogram":
            success = self.display_histogram(image_path)
        elif method == "plot":
            success = self.display_plot_data(image_path)
        else:
            console.print(f"[red]❌ Unknown display method: {method}[/red]")
            console.print("Available methods: info, ascii, blocks, histogram, plot")
            return False
        
        return success


def show_image_in_cli(image_path: str, method: str = "auto") -> bool:
    """
    Convenience function to display an image in the CLI.
    
    Args:
        image_path: Path to image file
        method: Display method
        
    Returns:
        True if successful
    """
    display = CLIImageDisplay()
    return display.display_image_cli(image_path, method)


def show_plot_preview(plot_path: str) -> bool:
    """
    Show a preview of a plot file in the CLI.
    
    Args:
        plot_path: Path to plot image
        
    Returns:
        True if successful  
    """
    display = CLIImageDisplay()
    
    # Show info first
    console.print("\\n" + "="*60)
    display.display_image_info(plot_path)
    
    console.print("\\n" + "="*60)
    console.print("[bold cyan]📈 Plot Preview Options:[/bold cyan]")
    console.print("1. 🎨 ASCII Art")
    console.print("2. 🌈 Color Blocks") 
    console.print("3. 📊 Color Histogram")
    console.print("4. 📁 Open in External Viewer")
    
    from rich.prompt import Prompt
    choice = Prompt.ask("Choose display method", choices=["1", "2", "3", "4"], default="1")
    
    if choice == "1":
        return display.display_as_ascii(plot_path)
    elif choice == "2":
        return display.display_color_blocks(plot_path)
    elif choice == "3":
        return display.display_histogram(plot_path)
    elif choice == "4":
        # Open externally
        try:
            if sys.platform.startswith('win'):
                os.startfile(plot_path)
            elif sys.platform.startswith('darwin'):
                import subprocess
                subprocess.run(['open', plot_path])
            else:
                import subprocess
                subprocess.run(['xdg-open', plot_path])
            console.print(f"[green]✅ Opened {plot_path} externally[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Error opening externally: {e}[/red]")
            return False


if __name__ == "__main__":
    # Test the CLI image display
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        method = sys.argv[2] if len(sys.argv) > 2 else "auto"
        show_image_in_cli(image_path, method)
    else:
        print("Usage: python cli_image_display.py <image_path> [method]")
        print("Methods: auto, info, ascii, blocks, histogram, plot")
