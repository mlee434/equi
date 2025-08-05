"""
Conversation management and UI functionality for Shakespeare RAG chatbot.
Handles interactive chat, command processing, and conversation export.
"""

from datetime import datetime
from typing import List, Dict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from shakespeare_core import ShakespeareCoreProcessor

console = Console()


class ShakespeareConversationManager:
    """Manages conversations and UI for the Shakespeare RAG chatbot"""
    
    def __init__(self):
        self.core_processor = ShakespeareCoreProcessor()
        self.conversation_history = []
    
    def export_conversation(self, filename: str) -> bool:
        """Export the conversation history to a text file"""
        try:
            # Ensure filename has .txt extension
            if not filename.endswith('.txt'):
                filename += '.txt'
            
            # Format the conversation
            formatted_conversation = "SHAKESPEARE RAG CHATBOT - Conversation Export\n"
            formatted_conversation += "=" * 60 + "\n\n"
            
            for message in self.conversation_history:
                if message["role"] == "user":
                    formatted_conversation += f"USER: {message['content']}\n\n"
                elif message["role"] == "assistant":
                    formatted_conversation += f"SHAKESPEARE BOT: {message['content']}\n\n"
                    formatted_conversation += "-" * 50 + "\n\n"
            
            # Remove the last separator
            formatted_conversation = formatted_conversation.rstrip("-" + "\n" + " ")
            
            # Add export timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_conversation += f"\n\nExported on: {timestamp}\n"
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(formatted_conversation)
            
            return True
            
        except Exception as e:
            console.print(f"❌ Error exporting conversation: {str(e)}", style="red")
            return False
    
    def show_help(self):
        """Show help information"""
        help_panel = Panel(
            """[bold blue]Shakespeare RAG Chatbot Help[/bold blue]

[bold]Available Commands:[/bold]
• Type any question about Shakespeare's works
• [cyan]/stats[/cyan] - Show collection statistics
• [cyan]/test[/cyan] - Test system connectivity
• [cyan]/all <query>[/cyan] - Search all collections (bypass AI selection)
• [cyan]/export[/cyan] - Save conversation to file
• [cyan]/new[/cyan] - Clear conversation history
• [cyan]/help[/cyan] - Show this help message
• [cyan]/quit[/cyan] or [cyan]/exit[/cyan] - Exit the chatbot

[bold]Example Queries:[/bold]
• "What does Hamlet say about death?"
• "Show me sonnets about love"
• "Who is Iago in Othello?"
• "What happens in Act 5 of Macbeth?"
• "Find passages about jealousy"
• "Tell me about Venus and Adonis"

[bold]Collections:[/bold]
• 🎭 [green]ShakespearePlays[/green] - All 37 plays
• 📜 [green]ShakespeareSonnets[/green] - The 154 sonnets  
• 🖋️ [green]ShakespearePoems[/green] - Other poetry works

[bold]Smart Collection Selection:[/bold]
The chatbot uses AI to automatically determine which collection(s) 
are most relevant for your query. Use [cyan]/all <query>[/cyan] to 
search all collections if you want comprehensive results.

[bold]Setup Requirements:[/bold]
1. Weaviate running: [cyan]docker-compose up -d[/cyan]
2. Data loaded: [cyan]python load_weaviate.py[/cyan]
3. OpenAI API key: [cyan]export OPENAI_API_KEY='your-key'[/cyan]
4. Use [cyan]/test[/cyan] command to verify setup

[bold]Technology Stack:[/bold]
• Vector Search: Weaviate + Ollama embeddings (nomic-embed-text)
• Text Generation: OpenAI GPT-4o-mini
• Collection Selection: AI-powered relevance detection""",
            title="Help",
            border_style="blue"
        )
        console.print(help_panel)
    
    def show_stats(self):
        """Show collection statistics"""
        console.print("📊 Gathering collection statistics...", style="blue")
        stats = self.core_processor.get_collection_stats()
        
        if not stats:
            console.print("❌ Unable to retrieve statistics", style="red")
            return
        
        table = Table(title="Shakespeare Collections Statistics")
        table.add_column("Collection", style="cyan", no_wrap=True)
        table.add_column("Objects", style="magenta")
        table.add_column("Description", style="green")
        
        descriptions = {
            "plays": "All dramatic works (37 plays)",
            "sonnets": "Shakespeare's 154 sonnets",
            "poems": "Other poetry (Venus & Adonis, etc.)"
        }
        
        collection_names = {
            "plays": "ShakespearePlays",
            "sonnets": "ShakespeareSonnets",
            "poems": "ShakespearePoems"
        }
        
        for name, count in stats.items():
            table.add_row(
                collection_names.get(name, name),
                str(count),
                descriptions.get(name, "")
            )
        
        console.print(table)
    
    def process_command(self, user_input: str) -> bool:
        """Process special commands. Returns True if command was handled, False if it's a regular query"""
        command = user_input.lower().strip()
        
        # Exit commands
        if command in ['/quit', '/exit', 'quit', 'exit']:
            console.print("👋 Goodbye! Thanks for exploring Shakespeare with me!", style="green")
            return True
        
        # Help command
        elif command == '/help':
            self.show_help()
            return True
        
        # Stats command
        elif command == '/stats':
            self.show_stats()
            return True
        
        # Test command
        elif command == '/test':
            self.core_processor.test_system()
            return True
        
        # Export command
        elif command == '/export':
            if not self.conversation_history:
                console.print("❌ No conversation to export", style="yellow")
                return True
            
            filename = Prompt.ask("📄 Enter filename (without extension)")
            if filename:
                if self.export_conversation(filename):
                    console.print(f"✅ Conversation exported to '{filename}.txt'", style="green")
                else:
                    console.print("❌ Failed to export conversation", style="red")
            else:
                console.print("❌ No filename provided, export cancelled", style="yellow")
            return True
        
        # New conversation command
        elif command == '/new':
            self.conversation_history = []
            console.print("🗑️ Conversation history cleared", style="green")
            return True
        
        # All collections search command
        elif command.startswith('/all '):
            query = user_input[5:].strip()  # Remove '/all ' prefix
            if query:
                with console.status("[bold green]Thinking...", spinner="dots"):
                    response = self.core_processor.process_query_all_collections(query, self.conversation_history)
                
                # Display response
                response_panel = Panel(
                    response,
                    title="[bold green]Shakespeare Bot (All Collections)[/bold green]",
                    border_style="green"
                )
                console.print(response_panel)
                
                # Add to conversation history
                self.conversation_history.append({"role": "user", "content": query})
                self.conversation_history.append({"role": "assistant", "content": response})
            else:
                console.print("Please provide a query after /all command", style="yellow")
            return True
        
        # Not a command
        return False
    
    def run_interactive(self, initial_query: str = None):
        """Run the interactive chat session"""
        # Initialize the core processor
        if not self.core_processor.initialize():
            console.print("❌ Failed to initialize Shakespeare RAG system", style="red")
            return
        
        # Welcome message
        welcome_panel = Panel(
            """[bold blue]🎭 Welcome to the Shakespeare RAG Chatbot! 🎭[/bold blue]

I can answer questions about Shakespeare's plays, sonnets, and poems using semantic search and AI.

Type [cyan]/help[/cyan] for commands or just ask me anything about Shakespeare!
Type [cyan]/quit[/cyan] to exit.""",
            title="Shakespeare RAG Chatbot",
            border_style="blue"
        )
        console.print(welcome_panel)
        
        # Process initial query if provided
        if initial_query:
            console.print(f"\n❓ Initial query: {initial_query}")
            with console.status("[bold green]Thinking...", spinner="dots"):
                response = self.core_processor.process_query(initial_query, self.conversation_history)
            
            response_panel = Panel(
                response,
                title="[bold green]Shakespeare Bot (Smart Search)[/bold green]",
                border_style="green"
            )
            console.print(response_panel)
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": initial_query})
            self.conversation_history.append({"role": "assistant", "content": response})
        
        # Interactive loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]").strip()
                
                if not user_input:
                    continue
                
                # Process commands
                if self.process_command(user_input):
                    if user_input.lower().strip() in ['/quit', '/exit', 'quit', 'exit']:
                        break
                    continue
                
                # Process regular query
                with console.status("[bold green]Thinking...", spinner="dots"):
                    response = self.core_processor.process_query(user_input, self.conversation_history)
                
                # Display response
                response_panel = Panel(
                    response,
                    title="[bold green]Shakespeare Bot (Smart Search)[/bold green]",
                    border_style="green"
                )
                console.print(response_panel)
                
                # Add to conversation history
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": response})
                
            except KeyboardInterrupt:
                console.print("\n👋 Goodbye! Thanks for exploring Shakespeare with me!", style="green")
                break
            except Exception as e:
                console.print(f"❌ Error: {e}", style="red")
        
        # Cleanup
        self.core_processor.close()