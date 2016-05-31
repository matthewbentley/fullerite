# coding=utf-8

"""
The CPUCollector collects CPU utilization metric using /proc/stat.

#### Dependencies

 * /proc/stat

"""

import diamond.collector
import os
import time
from diamond.collector import str_to_bool

try:
    import psutil
except ImportError:
    psutil = None


class CPUCollector(diamond.collector.Collector):

    PROC = '/proc/stat'
    INTERVAL = 1

    MAX_VALUES = {
        'user': diamond.collector.MAX_COUNTER,
        'nice': diamond.collector.MAX_COUNTER,
        'system': diamond.collector.MAX_COUNTER,
        'idle': diamond.collector.MAX_COUNTER,
        'iowait': diamond.collector.MAX_COUNTER,
        'irq': diamond.collector.MAX_COUNTER,
        'softirq': diamond.collector.MAX_COUNTER,
        'steal': diamond.collector.MAX_COUNTER,
        'guest': diamond.collector.MAX_COUNTER,
        'guest_nice': diamond.collector.MAX_COUNTER,
    }

    def get_default_config_help(self):
        config_help = super(CPUCollector, self).get_default_config_help()
        config_help.update({
            'percore':  'Collect metrics per cpu core or just total',
            'simple':   'only return aggregate CPU% metric',
            'normalize': 'for cpu totals, divide by the number of CPUs',
            'enableAggregation': 'Sends cpu.user + cpu.nice and cpu.irq + cpu.softirq',
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(CPUCollector, self).get_default_config()
        config.update({
            'path':     'cpu',
            'percore':  'True',
            'simple':   'False',
            'normalize': 'False',
            'enableAggregation': 'False',
        })
        return config

    def collect(self):
        """
        Collector cpu stats
        """

        def cpu_time_list():
            """
            get cpu time list
            """

            statFile = open(self.PROC, "r")
            timeList = statFile.readline().split(" ")[2:6]
            for i in range(len(timeList)):
                timeList[i] = int(timeList[i])
            statFile.close()
            return timeList

        def cpu_delta_time(interval):
            """
            Get before and after cpu times for usage calc
            """
            pre_check = cpu_time_list()
            time.sleep(interval)
            post_check = cpu_time_list()
            for i in range(len(pre_check)):
                post_check[i] -= pre_check[i]
            return post_check

        if os.access(self.PROC, os.R_OK):

            # If simple only return aggregate CPU% metric
            if str_to_bool(self.config['simple']):
                dt = cpu_delta_time(self.INTERVAL)
                cpuPct = 100 - (dt[len(dt) - 1] * 100.00 / sum(dt))
                self.publish('percent', str('%.4f' % cpuPct))
                return True

            results = {}
            # Open file
            file = open(self.PROC)

            ncpus = -1  # dont want to count the 'cpu'(total) cpu.
            for line in file:
                if not line.startswith('cpu'):
                    continue

                ncpus += 1
                elements = line.split()

                cpu = elements[0]

                if cpu == 'cpu':
                    cpu = 'cpu.total'
                elif not str_to_bool(self.config['percore']):
                    continue

                results[cpu] = {}

                if len(elements) >= 2:
                    results[cpu]['user'] = elements[1]
                if len(elements) >= 3:
                    results[cpu]['nice'] = elements[2]
                if len(elements) >= 4:
                    results[cpu]['system'] = elements[3]
                if len(elements) >= 5:
                    results[cpu]['idle'] = elements[4]
                if len(elements) >= 6:
                    results[cpu]['iowait'] = elements[5]
                if len(elements) >= 7:
                    results[cpu]['irq'] = elements[6]
                if len(elements) >= 8:
                    results[cpu]['softirq'] = elements[7]
                if len(elements) >= 9:
                    results[cpu]['steal'] = elements[8]
                if len(elements) >= 10:
                    results[cpu]['guest'] = elements[9]
                if len(elements) >= 11:
                    results[cpu]['guest_nice'] = elements[10]

                if results[cpu]['user'] is not None and results[cpu]['nice'] is not None:
                    results[cpu]['user_mode'] = float(results[cpu]['user']) + float(results[cpu]['nice'])

                if results[cpu]['irq'] is not None and results[cpu]['softirq'] is not None:
                    results[cpu]['irq_softirq'] = float(results[cpu]['irq']) + float(results[cpu]['softirq'])

            # Close File
            file.close()

            metrics = {}

            for cpu in results.keys():
                stats = results[cpu]
                for s in stats.keys():
                    # Get Metric Name
                    metric_name = '.'.join([cpu, s])
                    # Get actual data
                    if (str_to_bool(self.config['normalize'])
                            and cpu == 'total' and ncpus > 0):
                        metrics[metric_name] = long(stats[s]) / ncpus
                    else:
                        metrics[metric_name] = long(stats[s])

            for metric_name in metrics.keys():
                metric_value = metrics[metric_name]
                if (str_to_bool(self.config['enableAggregation']) is False
                    and ('user_mode' in metric_name
                        or 'irq_softirq' in metric_name)):
                    continue
                if 'cpu.total' not in metric_name:
                    metric_name, stat = metric_name.split('.')
                    core = metric_name[3:]
                    metric_name = '.'.join(['cpu', stat])

                    self.dimensions = {
                        'core' : str(core),
                    }
                self.publish_cumulative_counter(metric_name, metric_value)
            return True

        else:
            if not psutil:
                self.log.error('Unable to import psutil')
                self.log.error('No cpu metrics retrieved')
                return None

            cpu_time = psutil.cpu_times(True)
            cpu_count = len(cpu_time)
            total_time = psutil.cpu_times()

            for i in range(0, len(cpu_time)):
                metric_name = 'cpu'

                self.dimensions = {
                    'core': str(i),
                }
                self.publish_cumulative_counter(metric_name + '.user',
                                             cpu_time[i].user)
                if hasattr(cpu_time[i], 'nice'):
                    self.dimensions = {
                        'core': str(i),
                    }
                    self.publish_cumulative_counter(metric_name + '.nice',
                                                 cpu_time[i].nice)

                self.dimensions = {
                    'core': str(i),
                }
                self.publish_cumulative_counter(metric_name + '.system',
                                             cpu_time[i].system)

                self.dimensions = {
                    'core': str(i),
                }
                self.publish_cumulative_counter(metric_name + '.idle',
                                             cpu_time[i].idle)

                if (str_to_bool(self.config['enableAggregation'])):
                    self.publish_cumulative_counter(metric_name + '.user_mode',
                                                float(cpu_time[i].user) + float(cpu_time[i].nice))

            metric_name = 'cpu.total'
            cpu_user = total_time.user / cpu_count
            self.publish_cumulative_counter(metric_name + '.user',
                                         cpu_user)
            if hasattr(total_time, 'nice'):
                cpu_nice = total_time.nice / cpu_count
                self.publish_cumulative_counter(metric_name + '.nice',
                                             cpu_nice)
                if (str_to_bool(self.config['enableAggregation'])):
                    self.publish_cumulative_counter(metric_name + '.user_mode',
                                                cpu_user + cpu_nice)
            self.publish_cumulative_counter(metric_name + '.system',
                                         total_time.system / cpu_count)
            self.publish_cumulative_counter(metric_name + '.idle',
                                         total_time.idle / cpu_count)
            return True

        return None
