"""
Main entry point for Shakespeare RAG chatbot.
Uses modular agent architecture for processing queries about Shakespeare's works.
"""

import argparse
import sys
from shakespeare_conversation import ShakespeareConversationManager


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Shakespeare RAG Chatbot - AI-powered Q&A about Shakespeare's works"
    )
    parser.add_argument(
        "--query", "-q",
        type=str, 
        required=False, 
        help="Initial question to ask (if not provided, starts in interactive mode)"
    )
    
    args = parser.parse_args()
    
    try:
        # Create conversation manager
        conversation_manager = ShakespeareConversationManager()
        
        # Start interactive session
        conversation_manager.run_interactive(initial_query=args.query)
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()