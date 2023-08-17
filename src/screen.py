import atexit
from blessed.terminal import Terminal

term = Terminal()

def write(*args) -> None:
    print(*args, end = '', flush = True)

class ScreenCtrl:
    
    def __init__(self, rows: int, use_atexit = True) -> None:
        self._rows: int = rows
        # Create usable space
        for i in range(self._rows - 1):  # First row is already created after running program
            write('\n')
        # Get pointer to first usable row
        write(term.move_up(self._rows - 1))
        self._offset: int = term.get_location()[0]
        # Link exit routine to end of execution
        if use_atexit:
            atexit.register(self.at_exit)

    def clear_area(self) -> None:
        self.reset_cursor()
        write(term.clear_eos)
        for i in range(self._rows):
            write(term.clear_eol)
        self.reset_cursor()

    def reset_cursor(self) -> None:
        write(term.move_yx(self._offset, 0))

    def at_exit(self) -> None:
        # Create a new line so program output doesn't get clobbered by shell prompt
        write(term.move_yx(self._offset + self._rows, 0) + '\n')


if __name__ == "__main__":
    # For testing
    sc = ScreenCtrl(3)

