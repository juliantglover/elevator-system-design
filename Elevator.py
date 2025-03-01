from operator import attrgetter
from enum import Enum
import logging

logging.basicConfig(level=logging.DEBUG)


class Direction(Enum):
    DOWN = -1
    IDLE = 0
    UP = 1

    def __str__(self):
        return self.name.capitalize()


class PickupRequest:

    def __init__(self, time, floor, direction, destination):
        self.time = time
        self.floor = floor
        self.direction = direction
        self.destination = destination


class Elevator:

    def __init__(self, floors, starting_floor=1):
        self.floors = floors
        self.direction = Direction.IDLE
        self.current_floor = starting_floor
        self.destination_requests = set()
        self.pickup_requests = []

    def has_pending_requests(self):
        return self.destination_requests or len(self.pickup_requests) > 0

    def request_car(self, request):
        self.pickup_requests.append(request)

    def report_state(self, time):
        logging.info(
            {
                "time": time,
                "direction": str(self.direction),
                "floor": self.current_floor,
            }
        )

    def request_floor(self, floor):
        self.destination_requests.add(floor)

    def report_pickup(self, time):
        logging.debug(f"Time: {time} - Picking up passengers at {self.current_floor}")

    def report_dropoff(self, time):
        logging.debug(f"Time: {time} - Dropping off passengers at {self.current_floor}")

    def has_pickup_requests(self):
        return len(self.pickup_requests) > 0

    def has_pickup_request_at_current_floor(self):
        return (
            self.has_pickup_requests()
            and self.pickup_requests[0].floor == self.current_floor
        )

    def has_dropoff_request_at_current_floor(self):
        return self.current_floor in self.destination_requests

    def handle_parallel_requests(self, time):
        # Pickup any passengers along the way of the current request
        if self.has_pickup_requests():
            pickups_to_discard = []

            for request_index, request in enumerate(self.pickup_requests):

                # Handle all requests moving in the same direction
                if request.floor == self.current_floor and (
                    self.has_pickup_requests()
                    and (self.pickup_requests[0].direction == request.direction)
                    and (request.direction == self.direction)
                ):
                    pickup_request = self.pickup_requests[request_index]
                    pickups_to_discard.append(request_index)
                    self.report_pickup(time)
                    self.destination_requests.add(pickup_request.destination)

                for pickup in sorted(pickups_to_discard, reverse=True):
                    self.pickup_requests.pop(pickup)

    def pickup_at_current_floor(self, time):
        if self.has_pickup_request_at_current_floor():
            self.report_pickup(time)
            self.direction = self.pickup_requests[0].direction
            self.destination_requests.add(self.pickup_requests[0].destination)
            self.pickup_requests.pop(0)

    def drop_off_at_current_floor(self, time):
        if self.has_dropoff_request_at_current_floor():
            self.report_dropoff(time)
            self.destination_requests.remove(self.current_floor)

    def move(self, time):

        self.pickup_at_current_floor(time)
        self.drop_off_at_current_floor(time)

        # If elevator is idle then handle the first available pickup or drop off request.
        if self.direction == Direction.IDLE:
            if self.has_pickup_requests():
                if self.pickup_requests[0].floor > self.current_floor:
                    self.current_floor += 1
                    self.direction = Direction.UP

                elif self.pickup_requests[0].floor < self.current_floor:
                    self.current_floor -= 1
                    self.direction = Direction.DOWN

            elif self.destination_requests:
                if max(self.destination_requests) > self.current_floor:
                    self.current_floor += 1
                    self.direction = Direction.UP
                else:
                    self.current_floor -= 1
                    self.direction = Direction.DOWN

        elif self.direction == Direction.UP:
            # If elevator is moving up then ensure that a pick up or dropoff request exists for a higher floor, if not then start to move down or go idle.
            if (
                self.destination_requests
                and max(self.destination_requests) > self.current_floor
            ) or (
                self.has_pickup_requests()
                and self.pickup_requests[0].floor > self.current_floor
            ):
                self.current_floor += 1

            else:
                if self.destination_requests or self.has_pickup_requests():
                    self.direction = Direction.DOWN
                    self.current_floor -= 1
                else:
                    self.direction = Direction.IDLE

        elif self.direction == Direction.DOWN:

            # If elevator is moving down then ensure that a pick up or dropoff request exists for a lower floor, if not then start to move up or go idle.
            if (
                self.destination_requests
                and min(self.destination_requests) < self.current_floor
                or (
                    self.has_pickup_requests()
                    and self.pickup_requests[0].floor < self.current_floor
                )
            ):
                self.current_floor -= 1

            else:
                if self.destination_requests or self.has_pickup_requests():
                    self.direction = Direction.UP
                    self.current_floor += 1
                else:
                    self.direction = Direction.IDLE

        self.handle_parallel_requests(time)

        # If no requests exist then become idle
        if not self.has_pickup_requests() and not self.destination_requests:
            self.direction = Direction.IDLE

        self.report_state(time)


class ElevatorController:

    def __init__(self, elevator, requests):
        self.elevator = elevator
        self.requests = sorted(requests, key=attrgetter("time"), reverse=True)
        self.time = 0

    def run(self):

        # Simulate sending timed requests
        while len(self.requests) > 0 or self.elevator.has_pending_requests():
            while len(self.requests) > 0 and self.requests[-1].time <= self.time:
                new_request = self.requests.pop()
                self.elevator.request_car(new_request)
            self.elevator.move(self.time)
            self.time += 1


requests = [
    {"time": 1, "floor": 5, "direction": Direction.DOWN, "destination": 2},
    {"time": 2, "floor": 8, "direction": Direction.UP, "destination": 10},
    {"time": 3, "floor": 4, "direction": Direction.UP, "destination": 9},
    {"time": 7, "floor": 5, "direction": Direction.DOWN, "destination": 1},
]


floors = 10
elevator = Elevator(floors)

controller = ElevatorController(
    requests=list([PickupRequest(**request) for request in requests]), elevator=elevator
)

controller.run()


"""

The requests above will output the following logs:

INFO:root:{'time': 0, 'direction': 'Idle', 'floor': 1}
INFO:root:{'time': 1, 'direction': 'Up', 'floor': 2}
INFO:root:{'time': 2, 'direction': 'Up', 'floor': 3}
INFO:root:{'time': 3, 'direction': 'Up', 'floor': 4}
INFO:root:{'time': 4, 'direction': 'Up', 'floor': 5}
DEBUG:root:Time: 5 - Picking up passengers at 5
INFO:root:{'time': 5, 'direction': 'Down', 'floor': 4}
INFO:root:{'time': 6, 'direction': 'Down', 'floor': 3}
INFO:root:{'time': 7, 'direction': 'Down', 'floor': 2}
DEBUG:root:Time: 8 - Dropping off passengers at 2
INFO:root:{'time': 8, 'direction': 'Up', 'floor': 3}
DEBUG:root:Time: 9 - Picking up passengers at 4
INFO:root:{'time': 9, 'direction': 'Up', 'floor': 4}
INFO:root:{'time': 10, 'direction': 'Up', 'floor': 5}
INFO:root:{'time': 11, 'direction': 'Up', 'floor': 6}
INFO:root:{'time': 12, 'direction': 'Up', 'floor': 7}
DEBUG:root:Time: 13 - Picking up passengers at 8
INFO:root:{'time': 13, 'direction': 'Up', 'floor': 8}
INFO:root:{'time': 14, 'direction': 'Up', 'floor': 9}
DEBUG:root:Time: 15 - Dropping off passengers at 9
INFO:root:{'time': 15, 'direction': 'Up', 'floor': 10}
DEBUG:root:Time: 16 - Dropping off passengers at 10
INFO:root:{'time': 16, 'direction': 'Down', 'floor': 9}
INFO:root:{'time': 17, 'direction': 'Down', 'floor': 8}
INFO:root:{'time': 18, 'direction': 'Down', 'floor': 7}
INFO:root:{'time': 19, 'direction': 'Down', 'floor': 6}
DEBUG:root:Time: 20 - Picking up passengers at 5
INFO:root:{'time': 20, 'direction': 'Down', 'floor': 5}
INFO:root:{'time': 21, 'direction': 'Down', 'floor': 4}
INFO:root:{'time': 22, 'direction': 'Down', 'floor': 3}
INFO:root:{'time': 23, 'direction': 'Down', 'floor': 2}
INFO:root:{'time': 24, 'direction': 'Down', 'floor': 1}
DEBUG:root:Time: 25 - Dropping off passengers at 1
INFO:root:{'time': 25, 'direction': 'Idle', 'floor': 1}
"""
