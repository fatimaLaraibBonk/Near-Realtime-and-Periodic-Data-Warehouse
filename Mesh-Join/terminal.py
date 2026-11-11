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
import threads

#code
class TerminalWindowApp(App):

    #theme: pretty blue terminal with sky blue, royal blue and navy accents
    CSS = """
    Screen {
        background: #e3f2fd;
        color: #0d2a4a;
    }

    Header {
        background: #4a90e2;
        color: white;
    }

    Footer {
        background: #4a90e2;
        color: white;
    }

    Footer .footer-key--key {
        background: #4a90e2;
        color: #0a2f6b;
        text-style: bold;
    }

    Footer .footer-key--description {
        background: #4a90e2;
        color: white;
    }

    Horizontal {
        height: auto;
        background: #e3f2fd;
    }

    Static {
        background: #e3f2fd;
        color: #0d2a4a;
        padding: 1 2;
    }

    #main-terminal {
        background: #e3f2fd;
        border: heavy #1565c0;
        padding: 0 1;
    }

    RichLog {
        background: #f0f8ff;
        color: #0d2a4a;
        border: solid #2196f3;
        height: 1fr;
    }

    Input {
        background: #f0f8ff;
        color: #0d2a4a;
        border: tall #6fa8dc;
    }

    Input:focus {
        border: tall #2196f3;
    }

    Input:disabled {
        border: tall #a0aab4;
    }

    Input > .input--placeholder {
        color: #7fa6cc;
    }

    Input > .input--cursor {
        background: #2196f3;
        color: white;
    }
    #db_host,
    #db_port,
    #db_username,
    #db_password {
        display: None;
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
        self.db_host=""
        self.db_port=""
        self.db_username=""
        self.db_password=""
        self.link=""
        self.settings=None 
        #stats and things that we can change
        self.peak=80
        self.non_peak=10
        self.mode="both" #default online/periodic/both 
        self.speed="peak" #default peak/nonpeal
        self.rate=self.peak #whaterver rate to run 
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
                    placeholder="Enter database host...",
                    id="db_host",
                )
                yield Input(
                    placeholder="Enter database port...",
                    id="db_port"
                )
                yield Input(
                    placeholder="Enter database username...",
                    id="db_username"
                )

                yield Input(
                    placeholder="Enter database password...",
                    id="db_password"
                )
                yield Input(
                    placeholder="Enter online data source URL...",
                    id="link",
                    disabled=True
                )
                yield Input(placeholder="Enter new peak value...", id="peak")
                yield Input(placeholder="Enter new non-peak value...", id="non-peak")
                yield Input(placeholder="Type a command and press Enter...", id="terminal-input", disabled=True)    
        yield Footer()

    # initialization 

    def on_mount(self)->None:
        #this part runs immediately after the program is launched
        log=self.query_one("#console-log" , RichLog)
        log.write(f"[bold green]Near-Real Time and Periodic Data Warehouse.[/bold green].")
        log.write(f"[bold orange]Peak Rate=80 t/s, Non-Peak=10 t/s, 1 hour=60 secs.[/bold orange].")
        log.write(f"[cyan]Enter the database credentials (DB name and Password): [/cyan]")
        for widget_id in [
            "#db_host",
            "#db_port",
            "#db_username",
            "#db_password"
        ]:
            self.query_one(widget_id).display = True
        self.query_one("#db_host").focus()

    # input submissions 

    @on(Input.Submitted, "#db_host")
    def host_submitted(self, event:Input.Submitted)->None:
        self.db_host=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        log.write("[cyan]Host received![/cyan]")
        self.query_one("#db_port").focus()

    @on(Input.Submitted, "#db_port")
    def port_submitted(self, event:Input.Submitted)->None:
        self.db_port=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        log.write("[cyan]Port received![/cyan]")
        self.query_one("#db_username").focus()


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
        log.write("[cyan]Enter the link please: [/cyan]")
        answer=self.query_one("#link", Input)
        answer.disabled=False
        answer.focus()

    @on(Input.Submitted, "#link")
    def link_submitted(self, event: Input.Submitted)->None:
        self.link=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        log.write("[cyan]Link received! [/cyan]")
        main_object=main.clean_up_file(self.link, log, self.db_host, self.db_port, self.db_username, self.db_password)
        log.write("[bold green]Setup Complete :) [/bold green]")
        #after clean up boot up the threads
        self.settings=main.start_etl(main_object, self.rate, self.mode, self.speed)
        log.write("ETL started!")
        terminal=self.query_one("#terminal-input", Input)
        terminal.disabled=False
        for widget_id in [
            "#db_host",
            "#db_port",
            "#db_username",
            "#db_password"
        ]:
            self.query_one(widget_id).display = False
        terminal.focus()

    @on(Input.Submitted, "#peak")
    def on_peak_submitted(self, event: Input.Submitted) -> None:
        self.peak = event.value.strip()
        self.query_one("#console-log", RichLog).write(
            f"[green]Peak value updated to {self.peak}[/green]"
        )
        self.query_one("#peak").display = False
        self.query_one("#non-peak").display = True
        self.query_one("#non-peak", Input).focus()


    @on(Input.Submitted, "#non-peak")
    def on_non_peak_submitted(self, event: Input.Submitted) -> None:
        self.non_peak = event.value.strip()
        self.query_one("#console-log", RichLog).write(
            f"[green]Non-peak value updated to {self.non_peak}[/green]"
        )
        self.query_one("#non-peak").display = False
        self.query_one("#terminal-input", Input).display = True
        self.query_one("#terminal-input", Input).focus()
    # other commands 
    @on(Input.Submitted, "#terminal-input")
    def on_input_submitted(self, event: Input.Submitted)->None:
        command=event.value.strip()
        log=self.query_one("#console-log", RichLog)
        input_widget=self.query_one("#terminal-input", Input)
        if command:
            log.write(f"[yellow]$[/yellow] {command}")
            #command handling 

            #generic commands 
            if command.lower()=="help":
                log.write("Available commands: help, quit, peak, non-peak, online, periodic, both, status, change")
            elif command.lower()=="quit":
                log.write("Shutting down data warehouse simulation...")
                if self.settings:
                    self.settings.stop_event.set()
                    self.settings.config_changed.set()
                self.exit()            
            elif command.lower()=="clear":
                log.clear()

            #actual commands 
            #change rates from terminal 
            elif command.lower() == "change":
                log.write("[red]Change values for peak and non-peak[/red]")
                self.query_one("#terminal-input").display = False
                self.query_one("#peak").display = True
                self.query_one("#peak", Input).focus()

            #switch speeds 
            elif command.lower()=="peak":
                log.write(f"[red]Switched to peak mode[/red]")
                self.speed="peak"
                self.rate=self.peak
                if self.settings:
                    self.settings.update_speed("peak")
                    self.settings.update_rate(self.rate)

            elif command.lower()=="non-peak":
                log.write(f"[red]Switced to non-peak mode[/red]")
                self.speed="non-peak"
                self.rate=self.non_peak
                if self.settings:
                    self.settings.update_speed("non-peak")
                    self.settings.update_rate(self.rate)

            #switch modes 
            elif command.lower()=="online":
                log.write(f"[red]Switched to online-only mode[/red]")
                self.mode="online"
                if self.settings:
                    self.settings.update_mode("online")

            elif command.lower()=="periodic":
                log.write(f"[red]Switched to periodic-only mode[/red]")
                self.mode="periodic"
                if self.settings:
                    self.settings.update_mode("periodic")

            elif command.lower()=="both":
                log.write(f"[red]Switch to using both periodic and online[/red]")
                self.mode="both"
                if self.settings:
                    self.settings.update_mode("both")

            #print current status 
            elif command.lower()=="status":
                log.write(f"[red]Showing current stats: [/red]")
                log.write(f"[black]• Peak: {self.peak}[/black]")
                log.write(f"[black]• Non-peak: {self.non_peak}[/black]")
                log.write(f"[black]• Mode: {self.mode}[/black]")
                log.write(f"[black]• Speed: {self.speed}[/black]")
            else:
                log.write("Unknown command.")

        input_widget.value=""
        

# running terminal 
if __name__ == "__main__":
    app=TerminalWindowApp()
    app.run()