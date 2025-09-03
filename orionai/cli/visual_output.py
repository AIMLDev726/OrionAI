"""
Visual Output Display System for CLI
====================================

Display plots, images, and other visual content in the CLI.
Support for storing, showing, and managing visual outputs.
"""

import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

# Image and plot libraries (optional imports)
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import PIL.Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from cli.config import ConfigManager

console = Console()


@dataclass
class VisualItem:
    """Visual item (plot, image, etc.)."""
    id: str
    type: str  # "plot", "image", "chart", "diagram"
    title: str
    file_path: str
    created_at: str
    description: str = ""
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class VisualOutputManager:
    """Manager for visual outputs (plots, images, etc.)."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        # Use session image folder or default to 'visual_outputs'
        image_folder = getattr(self.config.session, 'image_folder', 'visual_outputs')
        self.output_dir = Path(image_folder)
        self.output_dir.mkdir(exist_ok=True)
        
        self.catalog_file = self.output_dir / 'catalog.json'
        self.items: Dict[str, VisualItem] = {}
        
        self._load_catalog()
    
    def _load_catalog(self):
        """Load visual items catalog."""
        if self.catalog_file.exists():
            try:
                with open(self.catalog_file, 'r') as f:
                    data = json.load(f)
                    
                for item_data in data.get('items', []):
                    item = VisualItem(**item_data)
                    self.items[item.id] = item
            except Exception as e:
                console.print(f"[red]Error loading catalog: {e}[/red]")
    
    def _save_catalog(self):
        """Save visual items catalog."""
        try:
            data = {
                'items': [
                    {
                        'id': item.id,
                        'type': item.type,
                        'title': item.title,
                        'file_path': item.file_path,
                        'created_at': item.created_at,
                        'description': item.description,
                        'tags': item.tags,
                        'metadata': item.metadata
                    }
                    for item in self.items.values()
                ]
            }
            
            with open(self.catalog_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving catalog: {e}[/red]")
    
    def add_item(self, item: VisualItem) -> bool:
        """Add a visual item to the catalog."""
        try:
            self.items[item.id] = item
            self._save_catalog()
            return True
        except Exception as e:
            console.print(f"[red]Error adding item: {e}[/red]")
            return False
    
    def remove_item(self, item_id: str) -> bool:
        """Remove a visual item."""
        try:
            if item_id in self.items:
                item = self.items[item_id]
                
                # Remove file if it exists
                file_path = Path(item.file_path)
                if file_path.exists():
                    file_path.unlink()
                
                # Remove from catalog
                del self.items[item_id]
                self._save_catalog()
                return True
            return False
        except Exception as e:
            console.print(f"[red]Error removing item: {e}[/red]")
            return False
    
    def get_item(self, item_id: str) -> Optional[VisualItem]:
        """Get a visual item by ID."""
        return self.items.get(item_id)
    
    def list_items(self, item_type: str = None, tags: List[str] = None) -> List[VisualItem]:
        """List visual items with optional filtering."""
        items = list(self.items.values())
        
        if item_type:
            items = [item for item in items if item.type == item_type]
        
        if tags:
            items = [item for item in items if any(tag in item.tags for tag in tags)]
        
        # Sort by creation date (newest first)
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items
    
    def create_plot_from_data(self, data: Any, plot_type: str = "line", title: str = "Plot", **kwargs) -> Optional[str]:
        """Create a plot from data."""
        if not MATPLOTLIB_AVAILABLE:
            console.print("[red]Matplotlib not available. Install with: pip install matplotlib[/red]")
            return None
        
        try:
            plt.figure(figsize=(10, 6))
            
            if plot_type == "line":
                if isinstance(data, dict):
                    for label, values in data.items():
                        plt.plot(values, label=label)
                    plt.legend()
                else:
                    plt.plot(data)
            
            elif plot_type == "bar":
                if isinstance(data, dict):
                    plt.bar(data.keys(), data.values())
                else:
                    plt.bar(range(len(data)), data)
            
            elif plot_type == "scatter":
                if isinstance(data, dict) and 'x' in data and 'y' in data:
                    plt.scatter(data['x'], data['y'])
                elif hasattr(data, '__len__') and len(data) >= 2:
                    plt.scatter(data[0], data[1])
            
            elif plot_type == "hist":
                plt.hist(data, bins=kwargs.get('bins', 20))
            
            elif plot_type == "pie":
                if isinstance(data, dict):
                    plt.pie(data.values(), labels=data.keys(), autopct='%1.1f%%')
                else:
                    plt.pie(data, autopct='%1.1f%%')
            
            plt.title(title)
            plt.grid(True, alpha=0.3)
            
            # Save the plot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"plot_{timestamp}.png"
            file_path = self.output_dir / filename
            
            plt.savefig(file_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            # Add to catalog
            item = VisualItem(
                id=f"plot_{timestamp}",
                type="plot",
                title=title,
                file_path=str(file_path),
                created_at=datetime.now().isoformat(),
                description=f"{plot_type.title()} plot",
                tags=[plot_type, "generated"],
                metadata={
                    "plot_type": plot_type,
                    "data_type": type(data).__name__,
                    **kwargs
                }
            )
            
            self.add_item(item)
            return item.id
            
        except Exception as e:
            console.print(f"[red]Error creating plot: {e}[/red]")
            return None
    
    def save_image(self, image_path: str, title: str = "", description: str = "", tags: List[str] = None) -> Optional[str]:
        """Save an image to the catalog."""
        try:
            source_path = Path(image_path)
            if not source_path.exists():
                console.print(f"[red]Image file not found: {image_path}[/red]")
                return None
            
            # Copy to output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"image_{timestamp}{source_path.suffix}"
            dest_path = self.output_dir / filename
            
            shutil.copy2(source_path, dest_path)
            
            # Get image info
            metadata = {}
            if PILLOW_AVAILABLE:
                try:
                    with PILImage.open(dest_path) as img:
                        metadata = {
                            "width": img.width,
                            "height": img.height,
                            "format": img.format,
                            "mode": img.mode
                        }
                except Exception:
                    pass
            
            # Add to catalog
            item = VisualItem(
                id=f"image_{timestamp}",
                type="image",
                title=title or f"Image {timestamp}",
                file_path=str(dest_path),
                created_at=datetime.now().isoformat(),
                description=description,
                tags=tags or ["imported"],
                metadata=metadata
            )
            
            self.add_item(item)
            return item.id
            
        except Exception as e:
            console.print(f"[red]Error saving image: {e}[/red]")
            return None
    
    def show_item(self, item_id: str, cli_display: bool = True) -> bool:
        """Show a visual item."""
        item = self.get_item(item_id)
        if not item:
            console.print(f"[red]Item not found: {item_id}[/red]")
            return False
        
        file_path = Path(item.file_path)
        if not file_path.exists():
            console.print(f"[red]File not found: {item.file_path}[/red]")
            return False
        
        # Try CLI display first if requested
        if cli_display:
            try:
                from .cli_image_display import show_image_in_cli
                
                console.print(f"\\n[bold cyan]📷 Displaying: {item.title}[/bold cyan]")
                if item.description:
                    console.print(f"[dim]{item.description}[/dim]")
                
                success = show_image_in_cli(str(file_path), "auto")
                if success:
                    console.print(f"[green]✅ Displayed {item.title} in CLI[/green]")
                    return True
                else:
                    console.print("[yellow]⚠️  CLI display failed, falling back to external viewer[/yellow]")
                    
            except ImportError as e:
                console.print(f"[yellow]⚠️  CLI display not available: {e}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠️  CLI display error: {e}[/yellow]")
        
        # Fallback to external viewer
        try:
            if sys.platform.startswith('win'):
                os.startfile(file_path)
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
            
            console.print(f"[green]✅ Opened {item.title} externally[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error opening file: {e}[/red]")
            return False
    
    def export_item(self, item_id: str, export_path: str) -> bool:
        """Export a visual item to a specified path."""
        item = self.get_item(item_id)
        if not item:
            console.print(f"[red]Item not found: {item_id}[/red]")
            return False
        
        try:
            source_path = Path(item.file_path)
            dest_path = Path(export_path)
            
            # Create directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_path, dest_path)
            console.print(f"[green]✅ Exported to {export_path}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error exporting item: {e}[/red]")
            return False


class VisualOutputInterface:
    """Rich CLI interface for visual outputs."""
    
    def __init__(self):
        self.manager = VisualOutputManager()
    
    def show_main_menu(self):
        """Show the main visual outputs menu."""
        while True:
            console.clear()
            
            # Header
            header = Panel.fit(
                "[bold blue]🎨 Visual Output Manager[/bold blue]\\n"
                "[dim]Display, store, and manage plots and images[/dim]",
                border_style="blue"
            )
            console.print(header)
            console.print()
            
            # Show statistics
            self._show_statistics()
            console.print()
            
            # Menu options
            menu_table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
            menu_table.add_column("Option", style="cyan", width=8)
            menu_table.add_column("Description", style="white")
            
            menu_table.add_row("1", "📊 Create Plot from Data")
            menu_table.add_row("2", "🖼️ Import Image")
            menu_table.add_row("3", "📋 List All Items")
            menu_table.add_row("4", "👁️ View Item")
            menu_table.add_row("5", "📤 Export Item")
            menu_table.add_row("6", "🗑️ Delete Item")
            menu_table.add_row("7", "🔍 Search Items")
            menu_table.add_row("8", "📁 Open Output Directory")
            menu_table.add_row("9", "⚙️ Settings")
            menu_table.add_row("0", "🔙 Back to Main Menu")
            
            console.print(Panel(menu_table, title="[bold]Visual Output Options[/bold]", border_style="green"))
            
            choice = Prompt.ask(
                "\\n[bold cyan]Choose an option[/bold cyan]",
                choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                default="0"
            )
            
            if choice == "0":
                break
            elif choice == "1":
                self._create_plot_interactive()
            elif choice == "2":
                self._import_image()
            elif choice == "3":
                self._list_items()
            elif choice == "4":
                self._view_item()
            elif choice == "5":
                self._export_item()
            elif choice == "6":
                self._delete_item()
            elif choice == "7":
                self._search_items()
            elif choice == "8":
                self._open_output_directory()
            elif choice == "9":
                self._show_settings()
            
            if choice != "0":
                input("\\nPress Enter to continue...")
    
    def _show_statistics(self):
        """Show visual output statistics."""
        items = self.manager.list_items()
        
        if not items:
            console.print(Panel(
                "[yellow]No visual items stored yet.[/yellow]",
                title="Statistics",
                border_style="yellow"
            ))
            return
        
        # Count by type
        type_counts = {}
        for item in items:
            type_counts[item.type] = type_counts.get(item.type, 0) + 1
        
        stats_table = Table(title="Statistics", box=box.ROUNDED)
        stats_table.add_column("Type", style="cyan")
        stats_table.add_column("Count", style="green", justify="right")
        
        for item_type, count in type_counts.items():
            stats_table.add_row(item_type.title(), str(count))
        
        stats_table.add_row("[bold]Total[/bold]", f"[bold]{len(items)}[/bold]")
        
        console.print(stats_table)
    
    def _create_plot_interactive(self):
        """Interactive plot creation."""
        console.clear()
        console.print(Panel.fit("[bold blue]📊 Create Plot[/bold blue]", border_style="blue"))
        console.print()
        
        if not MATPLOTLIB_AVAILABLE:
            console.print(Panel(
                "[red]Matplotlib not available![/red]\\n\\n"
                "Install with: pip install matplotlib",
                title="Missing Dependency",
                border_style="red"
            ))
            return
        
        # Get plot type
        plot_types = ["line", "bar", "scatter", "hist", "pie"]
        
        console.print("[bold cyan]Available plot types:[/bold cyan]")
        for i, plot_type in enumerate(plot_types, 1):
            console.print(f"{i}. {plot_type.title()}")
        
        choice = IntPrompt.ask(
            "\\nSelect plot type",
            choices=[str(i) for i in range(1, len(plot_types) + 1)]
        )
        plot_type = plot_types[choice - 1]
        
        # Get title
        title = Prompt.ask("Plot title", default=f"{plot_type.title()} Plot")
        
        # Get data
        console.print(f"\\n[bold cyan]Enter data for {plot_type} plot:[/bold cyan]")
        
        if plot_type == "line":
            data_str = Prompt.ask("Y values (comma-separated)", default="1,2,3,4,5")
            try:
                data = [float(x.strip()) for x in data_str.split(',')]
            except ValueError:
                console.print("[red]Invalid data format[/red]")
                return
        
        elif plot_type == "bar":
            labels_str = Prompt.ask("Labels (comma-separated)", default="A,B,C,D")
            values_str = Prompt.ask("Values (comma-separated)", default="10,20,15,25")
            
            try:
                labels = [x.strip() for x in labels_str.split(',')]
                values = [float(x.strip()) for x in values_str.split(',')]
                data = dict(zip(labels, values))
            except ValueError:
                console.print("[red]Invalid data format[/red]")
                return
        
        elif plot_type == "scatter":
            x_str = Prompt.ask("X values (comma-separated)", default="1,2,3,4,5")
            y_str = Prompt.ask("Y values (comma-separated)", default="2,4,1,5,3")
            
            try:
                x_data = [float(x.strip()) for x in x_str.split(',')]
                y_data = [float(x.strip()) for x in y_str.split(',')]
                data = {'x': x_data, 'y': y_data}
            except ValueError:
                console.print("[red]Invalid data format[/red]")
                return
        
        elif plot_type == "hist":
            data_str = Prompt.ask("Values (comma-separated)", default="1,2,2,3,3,3,4,4,5")
            try:
                data = [float(x.strip()) for x in data_str.split(',')]
            except ValueError:
                console.print("[red]Invalid data format[/red]")
                return
        
        elif plot_type == "pie":
            labels_str = Prompt.ask("Labels (comma-separated)", default="A,B,C,D")
            values_str = Prompt.ask("Values (comma-separated)", default="30,25,20,25")
            
            try:
                labels = [x.strip() for x in labels_str.split(',')]
                values = [float(x.strip()) for x in values_str.split(',')]
                data = dict(zip(labels, values))
            except ValueError:
                console.print("[red]Invalid data format[/red]")
                return
        
        # Create plot
        console.print("\\n[bold green]Creating plot...[/bold green]")
        
        with console.status("[bold green]Generating plot...", spinner="dots"):
            item_id = self.manager.create_plot_from_data(data, plot_type, title)
        
        if item_id:
            console.print(f"[green]✅ Plot created successfully! ID: {item_id}[/green]")
            
            if Confirm.ask("Open plot now?", default=True):
                self.manager.show_item(item_id)
        else:
            console.print("[red]❌ Failed to create plot[/red]")
    
    def _import_image(self):
        """Import an external image."""
        console.clear()
        console.print(Panel.fit("[bold blue]🖼️ Import Image[/bold blue]", border_style="blue"))
        console.print()
        
        # Get image path
        image_path = Prompt.ask("Image file path")
        
        if not Path(image_path).exists():
            console.print(f"[red]File not found: {image_path}[/red]")
            return
        
        # Get metadata
        title = Prompt.ask("Title", default=Path(image_path).stem)
        description = Prompt.ask("Description (optional)", default="")
        tags_str = Prompt.ask("Tags (comma-separated, optional)", default="")
        
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        # Import image
        console.print("\\n[bold green]Importing image...[/bold green]")
        
        with console.status("[bold green]Processing image...", spinner="dots"):
            item_id = self.manager.save_image(image_path, title, description, tags)
        
        if item_id:
            console.print(f"[green]✅ Image imported successfully! ID: {item_id}[/green]")
            
            if Confirm.ask("Open image now?", default=True):
                self.manager.show_item(item_id)
        else:
            console.print("[red]❌ Failed to import image[/red]")
    
    def _list_items(self):
        """List all visual items."""
        console.clear()
        console.print(Panel.fit("[bold blue]📋 Visual Items[/bold blue]", border_style="blue"))
        console.print()
        
        items = self.manager.list_items()
        
        if not items:
            console.print(Panel(
                "[yellow]No visual items found.[/yellow]",
                title="Empty Catalog",
                border_style="yellow"
            ))
            return
        
        # Filter options
        filter_type = Prompt.ask(
            "Filter by type (or press Enter for all)",
            choices=["", "plot", "image", "chart", "diagram"],
            default=""
        )
        
        if filter_type:
            items = [item for item in items if item.type == filter_type]
        
        if not items:
            console.print(f"[yellow]No {filter_type} items found.[/yellow]")
            return
        
        # Display items
        items_table = Table(title=f"Visual Items ({len(items)} total)", box=box.ROUNDED)
        items_table.add_column("ID", style="cyan", width=15)
        items_table.add_column("Type", style="yellow", width=8)
        items_table.add_column("Title", style="white", width=25)
        items_table.add_column("Created", style="blue", width=12)
        items_table.add_column("Tags", style="dim", width=20)
        
        for item in items[:20]:  # Show first 20 items
            created_date = item.created_at[:10]  # YYYY-MM-DD
            tags_str = ", ".join(item.tags[:3])  # First 3 tags
            if len(item.tags) > 3:
                tags_str += "..."
            
            items_table.add_row(
                item.id[:15],
                item.type,
                item.title[:25],
                created_date,
                tags_str
            )
        
        if len(items) > 20:
            items_table.add_row("...", "...", f"... and {len(items) - 20} more", "...", "...")
        
        console.print(items_table)
    
    def _view_item(self):
        """View a specific item."""
        console.clear()
        console.print(Panel.fit("[bold blue]👁️ View Item[/bold blue]", border_style="blue"))
        console.print()
        
        # Get item ID
        items = self.manager.list_items()
        if not items:
            console.print("[yellow]No items to view.[/yellow]")
            return
        
        # Show recent items for selection
        console.print("[bold cyan]Recent items:[/bold cyan]")
        for i, item in enumerate(items[:10], 1):
            console.print(f"{i}. {item.id} - {item.title}")
        
        choice = Prompt.ask("\\nEnter item ID or number (1-10)")
        
        # Parse choice
        if choice.isdigit() and 1 <= int(choice) <= min(10, len(items)):
            item = items[int(choice) - 1]
        else:
            item = self.manager.get_item(choice)
        
        if not item:
            console.print(f"[red]Item not found: {choice}[/red]")
            return
        
        # Show item details
        details_table = Table(title=f"Item Details: {item.title}", box=box.ROUNDED)
        details_table.add_column("Property", style="cyan")
        details_table.add_column("Value", style="white")
        
        details_table.add_row("ID", item.id)
        details_table.add_row("Type", item.type)
        details_table.add_row("Title", item.title)
        details_table.add_row("Description", item.description or "None")
        details_table.add_row("Created", item.created_at)
        details_table.add_row("File Path", item.file_path)
        details_table.add_row("Tags", ", ".join(item.tags) or "None")
        
        # Add metadata
        if item.metadata:
            for key, value in item.metadata.items():
                details_table.add_row(f"Meta: {key}", str(value))
        
        console.print(details_table)
        console.print()
        
        # Action options
        if Confirm.ask("Open this item?", default=True):
            self.manager.show_item(item.id)
    
    def _export_item(self):
        """Export an item."""
        console.clear()
        console.print(Panel.fit("[bold blue]📤 Export Item[/bold blue]", border_style="blue"))
        console.print()
        
        # Get item
        items = self.manager.list_items()
        if not items:
            console.print("[yellow]No items to export.[/yellow]")
            return
        
        # Show items for selection
        console.print("[bold cyan]Available items:[/bold cyan]")
        for i, item in enumerate(items[:10], 1):
            console.print(f"{i}. {item.id} - {item.title}")
        
        choice = Prompt.ask("\\nEnter item ID or number (1-10)")
        
        # Parse choice
        if choice.isdigit() and 1 <= int(choice) <= min(10, len(items)):
            item = items[int(choice) - 1]
        else:
            item = self.manager.get_item(choice)
        
        if not item:
            console.print(f"[red]Item not found: {choice}[/red]")
            return
        
        # Get export path
        export_path = Prompt.ask(
            "Export path",
            default=f"{item.title}.{Path(item.file_path).suffix[1:]}"
        )
        
        # Export
        if self.manager.export_item(item.id, export_path):
            console.print(f"[green]✅ Exported successfully![/green]")
        else:
            console.print("[red]❌ Export failed[/red]")
    
    def _delete_item(self):
        """Delete an item."""
        console.clear()
        console.print(Panel.fit("[bold blue]🗑️ Delete Item[/bold blue]", border_style="blue"))
        console.print()
        
        # Get item
        items = self.manager.list_items()
        if not items:
            console.print("[yellow]No items to delete.[/yellow]")
            return
        
        # Show items for selection
        console.print("[bold cyan]Available items:[/bold cyan]")
        for i, item in enumerate(items[:10], 1):
            console.print(f"{i}. {item.id} - {item.title}")
        
        choice = Prompt.ask("\\nEnter item ID or number (1-10)")
        
        # Parse choice
        if choice.isdigit() and 1 <= int(choice) <= min(10, len(items)):
            item = items[int(choice) - 1]
        else:
            item = self.manager.get_item(choice)
        
        if not item:
            console.print(f"[red]Item not found: {choice}[/red]")
            return
        
        # Confirm deletion
        if Confirm.ask(f"[bold red]Delete '{item.title}'? This cannot be undone.[/bold red]"):
            if self.manager.remove_item(item.id):
                console.print("[green]✅ Item deleted successfully![/green]")
            else:
                console.print("[red]❌ Failed to delete item[/red]")
    
    def _search_items(self):
        """Search for items."""
        console.clear()
        console.print(Panel.fit("[bold blue]🔍 Search Items[/bold blue]", border_style="blue"))
        console.print()
        
        # Get search criteria
        search_term = Prompt.ask("Search in titles/descriptions")
        
        items = self.manager.list_items()
        
        # Filter items
        matching_items = []
        for item in items:
            if (search_term.lower() in item.title.lower() or 
                search_term.lower() in item.description.lower() or
                any(search_term.lower() in tag.lower() for tag in item.tags)):
                matching_items.append(item)
        
        if not matching_items:
            console.print(f"[yellow]No items found matching '{search_term}'[/yellow]")
            return
        
        console.print(f"[green]Found {len(matching_items)} items:[/green]")
        
        # Display results
        results_table = Table(title=f"Search Results for '{search_term}'", box=box.ROUNDED)
        results_table.add_column("ID", style="cyan", width=15)
        results_table.add_column("Type", style="yellow", width=8)
        results_table.add_column("Title", style="white", width=25)
        results_table.add_column("Match", style="green", width=30)
        
        for item in matching_items:
            # Find what matched
            match_reason = ""
            if search_term.lower() in item.title.lower():
                match_reason = "Title"
            elif search_term.lower() in item.description.lower():
                match_reason = "Description"
            else:
                matching_tags = [tag for tag in item.tags if search_term.lower() in tag.lower()]
                if matching_tags:
                    match_reason = f"Tags: {', '.join(matching_tags)}"
            
            results_table.add_row(
                item.id[:15],
                item.type,
                item.title[:25],
                match_reason[:30]
            )
        
        console.print(results_table)
    
    def _open_output_directory(self):
        """Open the output directory."""
        try:
            output_dir = self.manager.output_dir
            
            if sys.platform.startswith('win'):
                os.startfile(output_dir)
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.run(['open', output_dir])
            else:  # Linux
                subprocess.run(['xdg-open', output_dir])
            
            console.print(f"[green]✅ Opened {output_dir}[/green]")
        except Exception as e:
            console.print(f"[red]Error opening directory: {e}[/red]")
    
    def _show_settings(self):
        """Show visual output settings."""
        console.clear()
        console.print(Panel.fit("[bold blue]⚙️ Visual Output Settings[/bold blue]", border_style="blue"))
        console.print()
        
        # Current settings
        settings_table = Table(title="Current Settings", box=box.ROUNDED)
        settings_table.add_column("Setting", style="cyan")
        settings_table.add_column("Value", style="white")
        
        settings_table.add_row("Output Directory", str(self.manager.output_dir))
        settings_table.add_row("Total Items", str(len(self.manager.items)))
        settings_table.add_row("Matplotlib Available", str(MATPLOTLIB_AVAILABLE))
        settings_table.add_row("Pillow Available", str(PILLOW_AVAILABLE))
        settings_table.add_row("NumPy Available", str(NUMPY_AVAILABLE))
        
        console.print(settings_table)
        console.print()
        
        # Installation help
        missing_deps = []
        if not MATPLOTLIB_AVAILABLE:
            missing_deps.append("matplotlib")
        if not PILLOW_AVAILABLE:
            missing_deps.append("Pillow")
        if not NUMPY_AVAILABLE:
            missing_deps.append("numpy")
        
        if missing_deps:
            console.print(Panel(
                f"[yellow]Missing dependencies:[/yellow] {', '.join(missing_deps)}\\n"
                f"[dim]Install with: pip install {' '.join(missing_deps)}[/dim]",
                title="Dependencies",
                border_style="yellow"
            ))


def show_visual_output_menu(console: Console = None):
    """Show the visual output management menu."""
    if console is None:
        console = Console()
    
    interface = VisualOutputInterface()
    interface.show_main_menu()


if __name__ == "__main__":
    show_visual_output_menu()
