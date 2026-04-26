CXX      := g++
CXXFLAGS := -std=c++17 -Wall -Wextra -O2

TARGET   := periscopic
SRCS     := laplace.cpp min_heap.cpp table_size_estimator.cpp main.cpp
OBJS     := $(SRCS:.cpp=.o)

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET) *.o
