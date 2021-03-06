import angr

import logging
l = logging.getLogger(name=__name__)

class deallocate(angr.SimProcedure):
    #pylint:disable=arguments-differ

    def run(self, addr, length): #pylint:disable=unused-argument
        # return code (see deallocate() docs)
        r = self.state.solver.ite_cases((
                (addr % 0x1000 != 0, self.state.cgc.EINVAL),
                (length == 0, self.state.cgc.EINVAL),
                (self.state.cgc.addr_invalid(addr), self.state.cgc.EINVAL),
                (self.state.cgc.addr_invalid(addr + length), self.state.cgc.EINVAL),
            ), self.state.solver.BVV(0, self.state.arch.bits))

        if self.state.solver.symbolic(addr):
            l.warning("Concretizing symbolic address passed to deallocate to max_int")

        addr = self.state.solver.max_int(addr)

        # into a page
        page_size = self.state.memory.mem._page_size
        base_page_num = addr // page_size

        if self.state.solver.symbolic(length):
            l.warning("Concretizing symbolic length passed to deallocate to max_int")

        length = self.state.solver.max_int(length)
        aligned_length = ((length + 0xfff) // 0x1000) * 0x1000

        # only add sinkholes and unmap on success
        if self.state.solver.max_int(r) == 0:

            # shorten length
            allowed_pages = 0
            while allowed_pages * page_size < aligned_length and \
                    base_page_num + allowed_pages in self.state.memory.mem._pages:
                allowed_pages += 1

            if allowed_pages == 0:
                return r

            allowed_length = allowed_pages * page_size
            self.state.cgc.add_sinkhole(addr, allowed_length)

            self.state.memory.unmap_region(addr, allowed_length)

        return r
