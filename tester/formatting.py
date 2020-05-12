class Format:
    def __init__(self, **kwargs):
        self.indent = " "
        self.line_f = 8*"-"
        self._new_line = "\n"
        self.bar = 50*"/"

        for k,v in kwargs.items():
            setattr(self, k, v)

    def new_line(self, str_, count=0):
        s = (self._new_line, 
            count*self.indent+str_)
        return "".join(s)
    
    def header(self, str_):
        s = (self._new_line, self.line_f, str_, self.line_f)
        return "".join(s)

    def show(self, s="s", **kwargs):
        s = getattr(self, s)
        s = "".join(s)
        print(s.format(**self.__dict__))

class FormatInfo(Format):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.success_rate = kwargs["success"] / kwargs["test_count"]
        self.failure_rate = kwargs["failure"] / kwargs["test_count"]

        self.test_complete = """Test complete"""
        self.s = (self.bar,
                    self._new_line,
                    self.new_line("{name} completed in {test_time}s"),
                    self.new_line("Average time per request: {mean}s"),
                    self._new_line,
                    self.header("Summary"),
                    self.new_line("Overall:"),
                    self.new_line("Success: {success_rate:.0%} ({success}/{test_count})", 2),
                    self.new_line("Failure: {failure_rate:.0%} ({failure}/{test_count})", 2),
                    self._new_line,
                    self.new_line("Timing:"),
                    self.new_line("Total test time: {test_time}s", 2),
                    self.new_line("Avg time: {mean}s", 2),
                    self.new_line("Max time: {max}s", 2),
                    self.new_line("Min time: {min}s", 2),
                    self._new_line*2,
                    self.bar
                            )

