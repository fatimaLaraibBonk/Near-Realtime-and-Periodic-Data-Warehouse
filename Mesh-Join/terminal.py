# 24i2504
# terminal simulation for better shapped outputs 

#inputs before running
#database credentials and path of the online file

#commands 
#online, periodic, both, peak, non-peak, status, quit 

#libraries 
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, RichLog
from textual import on
import main

#code
class TerminalWindowApp(App):

    #theme: white terminal with orange, black, red and green
    CSS = """
    Screen {
        background: white;
        color: black;
    }

    Header {
        background: orange;
        color: black;
    }

    Footer {
        background: orange;
        color: black;
    }

    Footer .footer-key--key {
        background: orange;
        color: red;
        text-style: bold;
    }

    Footer .footer-key--description {
        background: orange;
        color: black;
    }

    Horizontal {
        height: auto;
        background: white;
    }

    Static {
        background: white;
        color: black;
        padding: 1 2;
    }

    #main-terminal {
        background: white;
        border: heavy black;
        padding: 0 1;
    }

    RichLog {
        background: white;
        color: black;
        border: solid green;
        height: 1fr;
    }

    Input {
        background: white;
        color: black;
        border: tall black;
    }

    Input:focus {
        border: tall orange;
    }

    Input:disabled {
        border: tall red;
    }

    Input > .input--placeholder {
        color: red;
    }

    Input > .input--cursor {
        background: green;
        color: white;
    }
    """

    #keyboard shortcuts
    BINDINGS=[
        ("q", "quit", "quit data warehouse simulation"),
        ("o", "online", "switch to online data alone"),
        ("r", "periodic", "switch to periodic data alone"),
        ("b", "both", "switch to using both data"),
        ("p", "peak", "switch to peak"),
        ("n", "non-peak", "switch to non-peak"),
        ("s", "status", "view status"),
        ("m", "change", "change rates")
    ]

    def __init__(self):
        super().__init__()
        self.db_username=""
        self.db_password=""
        self.link=""
        self.choice=""

    def compose(self)->ComposeResult:
        #yields widgets to build the layout components
        yield Header(show_clock=True)

        with Horizontal():
            yield Static(
                "[bold orange]Data Warehouse Simulation[/bold orange]\n\n"
                "•[bold black]By:[/bold black] [green]Fatima Laraib[/green]\n"
                "•[bold black]Engine:[/bold black] [bright_magenta]Python and SQL[/bright_magenta]\n"
                "•Press [bold red]q[/bold red] to exit."
            )
        with Vertical(id="main-terminal"):
                yield RichLog(id="console-log", markup=True)
                yield Input(
                    placeholder="Enter database name...",
                    id="db_username"
                )

                yield Input(
                    placeholder="Enter database password...",
                    id="db_password"
                )
                yield Input(
                    placeholder="Enter data choice...",
                    id="choice"
                )
                yield Input(
                    placeholder="Enter online data source URL...",
                    id="link",
                    disabled=True
                )
                yield Input(placeholder="Type a command and press Enter...", id="terminal-input", disabled=True)    
        yield Footer()

    # initialization 

    def on_mount(self)->None:
        #this part runs immediately after the program is launched
        log=self.query_one("#console-log" , RichLog)
        log.write(f"[bold green]Near-Real Time and Periodic Data Warehouse.[/bold green].")
        log.write(f"[cyan]Enter the database credentials (DB name and Password): [/cyan]")
        self.query_one("#db_username").focus()

    # input submissions 

    @on(Input.Submitted, "#db_username")
    def username_submitted(self, event: Input.Submitted)->None:
        self.db_username=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        log.write("[cyan]Username received! [/cyan]")
        self.query_one("#db_password").focus()

    @on(Input.Submitted, "#db_password")
    def password_submitted(self, event: Input.Submitted)->None:
        self.db_password=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        log.write("[cyan]Password received! [/cyan]")
        log.write("[black]Would you like to use pre-cleaned data or start from scratch (download and clean)? 0 for pre-cleaned, 1 for scratch.")
        self.query_one("#choice").focus()


    @on(Input.Submitted, "#choice")
    def choice_submitted(self, event: Input.Submitted)->None:
        self.choice=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        if self.link=="0":
            #use existing clean data
            log.write("Using pre-cleaned data")
            log.write("[bold green]Setup Complete :) [/bold green]")

            # quickly start up the stream and hourly periods
            main.start_etl()
            log.write("ETL started!")
            terminal=self.query_one("#terminal-input", Input)
            terminal.disabled=False
            terminal.focus()
        else:
            #so 1 will make us use the link
            log.write("[cyan]Enter the link please: [/cyan]")
            answer=self.query_one("#link", Input)
            answer.disabled=False
            answer.focus()

    @on(Input.Submitted, "#link")
    def link_submitted(self, event: Input.Submitted)->None:
        self.link=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        log.write("[cyan]Link received! [/cyan]")
        main.clean_up_file(self.link, log)
        log.write("[bold green]Setup Complete :) [/bold green]")
        terminal=self.query_one("#terminal-input", Input)
        terminal.disabled=False
        terminal.focus()

    # other commands 
    @on(Input.Submitted, "#terminal-input")
    def on_input_submitted(self, event: Input.Submitted)->None:
        command=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        input_widget=self.query_one("#terminal-input", Input)

        if command:
            log.write(f"[yellow]$[/yellow] {command}")
            #command handling 

            if command.lower()=="help":
                log.write("Available commands: help, quit, peak, non-peak, online, periodic, both, status, change")
            elif command.lower()=="quit":
                log.write("Shutting down data warehouse simulation...")
                self.exit()            
            elif command.lower()=="clear":
                log.clear()
            else:
                log.write("Unknown command.")

        input_widget.value=""
        

# running terminal 
if __name__ == "__main__":
    app=TerminalWindowApp()
    app.run()