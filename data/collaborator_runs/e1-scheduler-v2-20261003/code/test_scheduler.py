import concurrent.futures as cf
import threading
import unittest
from scheduler_v2 import lane,RoutedExecutor,process
import os


class SchedulerTests(unittest.TestCase):
    def test_fixed_endpoint_assignment(self):
        self.assertEqual(lane(({},4102,'pure-llm')),'llm-0')
        self.assertEqual(lane(({},4101,'llm-rl')),'llm-1')
        self.assertEqual(lane(({},4101,'rl')),'cpu')

    def test_lanes_are_separate_and_capped(self):
        release=threading.Event();started=threading.Event();counts={'cpu':0,'llm-0':0,'llm-1':0};lock=threading.Lock()
        def task(job):
            with lock:
                counts[lane(job)]+=1
                if counts=={'cpu':3,'llm-0':2,'llm-1':2}:started.set()
            release.wait(5)
        with RoutedExecutor(max_workers=8) as pool:
            jobs=[({},2,'pure-llm')]*3+[({},1,'llm')]*3+[({},1,'rule')]*3
            fs=[pool.submit(task,j) for j in jobs]
            try:self.assertTrue(started.wait(3));self.assertEqual(counts,{'cpu':3,'llm-0':2,'llm-1':2})
            finally:release.set()
            for f in cf.as_completed(fs):f.result()

    @unittest.skipUnless(os.name=='posix','Linux procfs')
    def test_proc_stat_exit_status_index(self):
        import subprocess,time
        proc=subprocess.Popen(['sh','-c','exit 7'])
        for _ in range(100):
            s=process(proc.pid)
            if s and s['state']=='Z':break
            time.sleep(.01)
        self.assertEqual(os.waitstatus_to_exitcode(s['exit_status']),7)
        self.assertEqual(proc.wait(),7)


if __name__=='__main__':unittest.main()
