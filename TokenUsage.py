import datetime as dt


class TokenUsage:
    def __init__(self):
        self.cache_hit: int = 0
        self.cache_miss:int  = 0
        self.output:int  = 0
        hour = dt.datetime.now(dt.UTC).hour
        if (hour >= 1 and hour <= 4) or (hour >= 6 and hour <= 10):
            self._cache_hit_rate: float = 0.014
            self._cache_miss_rate: float = 0.44
            self._output_rate:float  = 1.32
        else:
            self._cache_hit_rate:float = 0.007
            self._cache_miss_rate:float = 0.22
            self._output_rate:float = 0.66

    def add(self, usage_metadata):
        _input = usage_metadata["input_tokens"]
        _cache_hit = usage_metadata["input_token_details"]["cache_read"]
        self.cache_hit += _cache_hit
        self.cache_miss += _input - _cache_hit
        self.output += usage_metadata["output_tokens"]

    def costs(self) -> tuple[float, float, float]:
        cache_hits = (self.cache_hit / 1000000) * self._cache_hit_rate
        cache_miss = (self.cache_miss / 1000000) * self._cache_miss_rate
        output = (self.output / 1000000) * self._output_rate
        return (cache_hits, cache_miss, output)

    def calculate(self):
        cache_hits, cache_miss, output = self.costs()
        print(f"Cache hit: {self.cache_hit} x {self._cache_hit_rate}/1M = {cache_hits:.4f}")
        print(f"Cache miss: {self.cache_miss} x {self._cache_miss_rate}/1M = {cache_miss:.4f}")
        print(f"Output: {self.output} x {self._output_rate}/1Μ = {output:.4f}")
        print(f"Total: {cache_hits + cache_miss + output:.4f}")
