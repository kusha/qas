from setuptools import setup

setup(name='qas',
      version='0.1',
      description='Question answering system '
                  'with the schema-agnostic '
                  'graph-based approach.',
      url='http://github.com/kusha/qas',
      author='Mark Birger',
      author_email='xbirge00@stud.fit.vutbr.cz',
      license='MIT',
      packages=['qas'],
      entry_points={
        'console_scripts': [
          'qa_system_env = qas.__main__:main',
        ],
      }
      )
