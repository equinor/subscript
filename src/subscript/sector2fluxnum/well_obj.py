class Wells:
    def __init__(self, well_info):

        self.completions = []
        self.well_list = []
        self.well_info = well_info

    def get_well_list(self):

        return self.well_list

    def get_completion_list(self):

        return self.completions

    def find_completions(self):

        # Go through all the wells:
        for well_time_line in self.well_info:
            for well_state in well_time_line:
                if well_state.name() not in self.well_list:
                    # Add well to well list
                    self.well_list.append(well_state.name())
                    # Add slot for well completions
                    self.completions.append([])

                    for completion in well_state.globalConnections():
                        comp_ijk = completion.ijk()

                        if comp_ijk not in self.completions[-1]:
                            self.completions[-1].append(comp_ijk)

                else:
                    ind = self.well_list.index(well_state.name())

                    for completion in well_state.globalConnections():
                        comp_ijk = completion.ijk()

                        if comp_ijk not in self.completions[ind]:
                            self.completions[ind].append(comp_ijk)
