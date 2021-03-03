from tabulate import tabulate


class BlockSummaryMixin:
    """ Displays all structural information about a block: ports, children and connections """

    @property
    def name(self):
        raise NotImplementedError

    @property
    def blocks(self):
        raise NotImplementedError

    @property
    def ports(self):
        raise NotImplementedError

    @property
    def port_graph__(self):
        raise NotImplementedError

    @property
    def full_name(self):
        raise NotImplementedError

    def summary(self):
        columns = ["In", "Out", "AuxIn", "AuxOut", "Children", "Port Links"]
        In = '\n'.join([x.name for x in self.ports.In])
        Out = '\n'.join([x.name for x in self.ports.Out])
        AuxIn = '\n'.join([x.name for x in self.ports.AuxIn])
        AuxOut = '\n'.join([x.name for x in self.ports.AuxOut])
        children = '\n'.join([f'{x.name} ({x.__class__.__name__})' for x in self.blocks])

        def parse_port(port):
            if port in self.ports:
                return port.name
            else:
                return f'{port.block.name}.{port.name}'

        links = '\n'.join([f'{parse_port(p1)}->{parse_port(p2)}'
                           for p1, p2 in self.port_graph__.edges()])

        table = tabulate([[In, Out, AuxIn, AuxOut, children, links]], columns, tablefmt="grid")

        summary = '\n'.join([f'Name: {self.name}',
                             f'Class: {self.__class__.__name__}',
                             f'Full Name: {self.full_name}',
                             f'{table}'])
        return summary
