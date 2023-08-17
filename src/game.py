from enum import Enum
from urllib.request import urlopen
from blessed.terminal import Terminal
from blessed.keyboard import Keystroke
from screen import ScreenCtrl, write

term = Terminal()

word_lists: dict[int, str] = {
    5: "https://raw.githubusercontent.com/charlesreid1/five-letter-words/master/sgb-words.txt"
}

class Color(Enum):
    GRAY   = 0
    YELLOW = 1
    GREEN  = 2

color_ansi: dict[Color, str] = {
    Color.GRAY:   term.on_bright_black,
    Color.YELLOW: term.on_yellow,
    Color.GREEN:  term.on_green
}

color_emoji: dict[Color, str] = {
    Color.GRAY:   '⬛',
    Color.YELLOW: "🟨",
    Color.GREEN:  "🟩"
}

def half_to_full(char: str) -> str:
    assert(65 <= ord(char) <= 90)
    return chr(ord(char) + 0xfee0)

class Wordle:

    def __init__(self, length: int = 5, limit: int = 6, *, word: str | None = None, hard: bool = False, share: bool = False, check_valid: bool = False) -> None:
        self._length = length
        self._limit = limit
        self._hard = hard
        self._share_result = share
        self._check_valid = check_valid
        self._animate = False

        if self._check_valid:
            self._valid_words = self.get_valid_words()
        if word == None:
            self._word = self.get_random_word().upper()
        else:
            self._word = word.upper()
            if self._check_valid:
                assert(self.check_valid_word(self._word))
        self._guesses: list[str] = []
        self._colors: list[list[Color]] = []

    def make_screenctrl(self) -> ScreenCtrl:
        return ScreenCtrl(self._limit + 5, False)
    
    def get_valid_words(self) -> set[str]:
        words: set[str] = set()
        for word in urlopen(word_lists[self._length]):
            words.add(word.decode('utf-8').strip().upper())
        return words

    def make_guess(self, guess: str) -> bool:
        try:
            assert(guess.isalpha)
            assert(len(guess) == self._length)
        except AssertionError:
            return False
        guess = guess.upper()
        colors: list[Color] = [Color.GRAY for _ in range(self._length)]
        word = list(self._word)
        # Check for correct letters
        for i in range(self._length):
            if guess[i] == word[i]:
                colors[i] = Color.GREEN
                word[i] = '_'
        # Check for letters in wrong place
        for i in range(self._length):
            if colors[i] != Color.GREEN:
                if guess[i] in word:
                    colors[i] = Color.YELLOW
                    word[word.index(guess[i])] = '_'
        # Save guess
        self._guesses.append(guess)
        self._colors.append(colors)
        return True

    def get_random_word(self) -> str:
        pass

    def get_row(self, row: int) -> str:
        if row > self._limit:
            return ''
        elif row >= len(self._guesses):
            return color_ansi[Color.GRAY] + ('  ' * self._length) + term.normal
        else:
            out = term.bold
            for i in range(self._length):
                out += color_ansi[self._colors[row][i]] + half_to_full(self._guesses[row][i])
            out += term.normal
            return out
        
    def gen_row_str(self) -> str:
        for row in range(self._limit):
            yield self.get_row(row)

    def draw_game(self, scr: ScreenCtrl) -> None:
        scr.clear_area()
        scr.reset_cursor()
        write(term.move_down)
        guess_str = str(len(self._guesses))
        if self.finished() and not self.won():
            guess_str = "X"
        write(f"  Guess {guess_str}/{self._limit}{'*' if self._hard else ' '}" + '\n' + '\n')
        for row in self.gen_row_str():
            write('  ')
            if self._animate:
                with term.hidden_cursor():
                    pass
            else:
                write(row + '\n')
        write('\n')
        write(term.clear_eol)

    def draw_result(self) -> None:
        print("Copy the following to share your results:")
        guess_str = str(len(self._guesses))
        if self.finished() and not self.won():
            guess_str = "X"
        out = f"Guess {guess_str}/{self._limit}{'*' if self._hard else ' '}\n\n"
        for row in self._colors:
            for square in row:
                out += (color_emoji[square])
            out += '\n'
        print(out)

    def check_valid_word(self, word: str) -> bool:

        def check_len() -> bool:
            return True if len(word) == self._length else False
        
        def check_dict() -> bool:
            if self._check_valid:
                if word in self._valid_words:
                    return True
                return False
            return True
        
        def check_hard() -> bool:
            if self._hard:
                if len(self._guesses) == 0:
                    return True
                guess = list(word)
                for i in range(self._length):
                    if self._colors[-1][i] == Color.GREEN:
                        if guess[i] != self._guesses[-1][i]:
                            return False
                        guess[i] = '-'
                for i in range(self._length):
                    if self._colors[-1][i] == Color.YELLOW:
                        if not (self._guesses[-1][i] in guess):
                            return False
                        guess[guess.index(self._guesses[-1][i])] = '-'
            return True
        
        if not check_len():
            return (False, '')
        elif not check_dict():
            return (False, "Invalid word")
        elif not check_hard():
            return (False, "All clues must be used")
        else:
            return (True, '')

    def get_input(self) -> str:
        with term.cbreak():
            buffer: list[str] = []
            key = Keystroke()
            while True:
                valid, string = self.check_valid_word(''.join(buffer))
                write(term.clear_eol + term.clear_bol + term.move_x(0))
                write(f" >{term.bold}{term.red if len(buffer) == self._length and not valid else ''}{''.join([half_to_full(letter) for letter in buffer])}")
                with term.location():  # Restore cursor pos after writing string
                    write(f"  {term.normal}{string}")
                write(term.normal)
                key = term.inkey()
                if key.is_sequence:
                    if key.code == 343:  # Enter
                        if valid:
                            return ''.join(buffer)
                    elif key.code == 263:  # Backspace
                        if len(buffer) > 0:
                            buffer.pop()
                    elif key.code == 361:  # Escape
                        exit()
                else:
                    letter = str(key).upper()
                    if 65 <= ord(letter) <= 90:
                        if len(buffer) < self._length:
                            buffer.append(letter)

    def finished(self) -> bool:
        if len(self._colors) == 0:
            return False
        if (len(self._guesses) >= self._limit) or (self.won()):
            return True
        else:
            return False
        
    def won(self) -> bool:
        if self._colors[-1] == [Color.GREEN for _ in range(self._length)]:
            return True
        else:
            return False

    def do_game(self, scr: ScreenCtrl) -> None:
        while not self.finished():
            self.draw_game(scr)
            guess = self.get_input()
            self.make_guess(guess)
        self.draw_game(scr)
        if self._share_result:
            self.draw_result()



if __name__ == "__main__":
    w = Wordle(5, word = 'qualm', check_valid = True, hard = True)
    scr = w.make_screenctrl()
    w.do_game(scr)
    # w.make_guess('helen')
    # for row in w.gen_row_str():
    #     print(row)