from rich.syntax import Syntax
from rich.panel import Panel
from trade_engine.core.strategy_builder import AIStrategyBuilder
from trade_engine.core.stock_advisor import AIStockAdvisor
from trade_engine.config.llm_config import LLM_PROVIDER


class AIAdvisorMenu:
    """CLI menu for AI-powered strategy generation and stock analysis."""

    def __init__(self, interface):
        self.interface = interface
        self.provider = LLM_PROVIDER

    def show(self):
        """Display the AI advisor sub-menu."""
        while True:
            menu_options = [
                "Generate Strategy (AI)",
                "Stock Analysis",
                "Find Stocks by Criteria",
                "Configure LLM Provider",
                "Back to Main Menu"
            ]

            choice = self.interface.show_menu(menu_options, "AI Strategy Advisor")

            if choice == "Generate Strategy (AI)":
                self._generate_strategy()
            elif choice == "Stock Analysis":
                self._stock_analysis()
            elif choice == "Find Stocks by Criteria":
                self._find_stocks()
            elif choice == "Configure LLM Provider":
                self._configure_llm()
            elif choice == "Back to Main Menu":
                return

    def _generate_strategy(self):
        description = self.interface.input_prompt("Describe your trading strategy in English:\n> ")
        if not description.strip():
            self.interface.print_error("Description cannot be empty.")
            return

        try:
            builder = AIStrategyBuilder(provider=self.provider)
            code = self.interface.show_loading(
                "[bold cyan]AI is generating strategy code...[/bold cyan]",
                builder.generate_strategy_code,
                description
            )

            if code:
                # Display the generated code
                syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
                self.interface.console.print(Panel(syntax, title="[bold green]Generated Strategy[/bold green]", border_style="green"))

                # Ask to save
                save = self.interface.input_prompt("Save this strategy? (y/n): ")
                if save.lower() == "y":
                    filename = self.interface.input_prompt("Enter filename (without .py): ")
                    if filename.strip():
                        filepath = builder.save_strategy(code, filename)
                        self.interface.print_success(f"Strategy saved to: {filepath}")
                    else:
                        self.interface.print_error("Invalid filename.")
        except Exception as e:
            self.interface.print_error(f"Error: {e}")

    def _stock_analysis(self):
        symbol = self.interface.input_prompt("Enter stock symbol (e.g. RELIANCE.NS): ")

        analysis_types = ["comprehensive", "technical", "fundamental", "risk"]
        analysis_type = self.interface.show_menu(analysis_types + ["Back"], "Analysis Type")
        if analysis_type == "Back":
            return

        try:
            advisor = AIStockAdvisor(provider=self.provider)
            result = self.interface.show_loading(
                f"[bold cyan]AI is analyzing {symbol}...[/bold cyan]",
                advisor.analyze_stock,
                symbol, analysis_type
            )

            if result:
                self.interface.console.print(Panel(
                    result,
                    title=f"[bold green]{symbol} - {analysis_type.title()} Analysis[/bold green]",
                    border_style="green",
                    padding=(1, 2)
                ))
        except Exception as e:
            self.interface.print_error(f"Error: {e}")

    def _find_stocks(self):
        criteria = self.interface.input_prompt("Describe what you're looking for:\n> ")
        if not criteria.strip():
            self.interface.print_error("Criteria cannot be empty.")
            return

        count_str = self.interface.input_prompt("How many recommendations? [5]: ") or "5"
        try:
            count = int(count_str)
        except ValueError:
            count = 5

        try:
            advisor = AIStockAdvisor(provider=self.provider)
            result = self.interface.show_loading(
                "[bold cyan]AI is searching for stocks...[/bold cyan]",
                advisor.recommend_stocks,
                criteria, count
            )

            if result:
                self.interface.console.print(Panel(
                    result,
                    title="[bold green]Stock Recommendations[/bold green]",
                    border_style="green",
                    padding=(1, 2)
                ))
        except Exception as e:
            self.interface.print_error(f"Error: {e}")

    def _configure_llm(self):
        providers = ["openai", "claude", "gemini"]
        self.interface.print_info(f"Current provider: {self.provider}")
        choice = self.interface.show_menu(providers + ["Back"], "Select LLM Provider")
        if choice == "Back":
            return
        self.provider = choice
        self.interface.print_success(f"LLM provider set to: {self.provider}")
        self.interface.print_info("Note: Make sure the corresponding API key is set in your .env file.")


