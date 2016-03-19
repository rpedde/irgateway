import pipes
import subprocess


class Espeak(object):
    def __init__(self, voice='male3', speed=175, intonation=100, pitch=50):
        self.voice = voice
        self.speed = speed
        self.intonation = intonation
        self.pitch = pitch

    def say(self, what):
        what = pipes.quote(what)
        cmd = ['/usr/bin/espeak',
               '-v', self.voice,
               '-s', str(self.speed),
               '-p', str(self.pitch),
               '-k', str(self.intonation),
               what]
        subprocess.Popen(cmd)


if __name__ == '__main__':
    esp = Espeak()
    esp.say('this is a test')
