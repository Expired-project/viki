#!/usr/bin/env python3

import ast
import os
import subprocess
import json
import uuid

class Jobs():
    """ Jobs library for viki """

    ### Jobs internals

    def __init__(self):
        """ Initialize jobs handler
        Vars for use:
        home: Viki's home directory. Usually /usr/local/viki
        jobs_path: Path to Viki's jobs directory. Usually /usr/local/viki/jobs
        job_config_filename: Name of the config for each individual job. Usually 'config.json'
        """

        # Change to just /home/viki eventually
        self.home = "/usr/local/viki"

        # Path to the jobs directory relative to self.home
        self.jobs_path = self.home + "/" + "jobs"

        # Name of job configuration file
        self.job_config_filename = "config.json"

    def _quote_string(self, string, SingleQuote=True):
        """ Takes a string and returns it
        back surrounded by quotes
        """
        if SingleQuote:
            quote = "'"
        else:
            quote = '"'

        return quote + string + quote

    def _write_job_file(self, file, text):
        """ _write_job_file
        Takes a filename and textblob and
        attempts to write the text to that file
        """

        if not file or not text:
            return False

        # This will not work if the directory does not exist
        with open(file, 'w') as file_obj:
            file_obj.write(json.dumps(text))
            file_obj.close()

        return True

    def _read_job_file(self, file):
        """ _read_job_file
        Takes a filename and returns the string
        Filename must be the full path of the file, not just the name
        contents of that file or False if it does not exist
        """
        if not file:
            return False

        with open(file, 'r') as file_obj:
            ret = file_obj.read()
            file_obj.close()

        return ret

    def _run_shell_command(self, command, output_filename):
        """ _run_shell_command
        string:command Shell command to run
        string:file path Where the command results (stdout) are stored
        Runs the given command and stores results in a file
        Returns Tuple (True|False, Return code)
        """

        # Generate output file for run results
        output_file_obj = open(output_filename, 'a')

        # Generate a tmp sh file to run command from
        sh_script_name = 'viki-' + str(uuid.uuid4())
        with open(sh_script_name, 'w') as sh_script_obj:
            sh_script_obj.write(command)
            sh_script_obj.close()

        process = subprocess.Popen(
            [b'/bin/bash', b'-xc', command],
            stdout=output_file_obj,
            stderr=subprocess.STDOUT
        )

        while process.poll() is None:
            # Not finished
            pass

        return_code = process.poll()

        output_file_obj.close()
        self._dirty_rm_rf(sh_script_name)

        return (True, return_code) if return_code == 0 else (False, return_code)

    def _dirty_rm_rf(self, dir):
        """ Executes a quick and dirty rm -rf dirName
        Use subprocess because its easier to let bash do this than Python
        """
        subprocess.call(
            [b'/bin/bash', b'-c', 'rm -rf ' + dir]
        )

        return True


    ### Job functions

    def get_jobs(self):
        """
        List jobs in /usr/local/viki/jobs
        Takes no parameters
        """
        message = "Ok"
        success = 1
        jobs_list = []

        try:

            # Get all job dirs
            jobs_dir_ls = next(os.walk(self.jobs_path))
            jobs_list = jobs_dir_ls[1]

        except OSError as error:
            message = str(error)
            success = 0

        ret = { "success":success, "message":message, "jobs":jobs_list }

        return ret


    def get_job_by_name(self, name):
        """
        Get details of a single job by name
        string:name Name of specific job
        """
        message = "Ok"
        success = 1
        contents = ""

        try:

            if name is None:
                raise ValueError('Missing required field: jobName')

            job_dir = self.jobs_path + "/" + name

            if os.path.isdir(job_dir) and os.path.exists(job_dir + "/" + self.job_config_filename):
                contents = self._read_job_file(job_dir + "/" + self.job_config_filename)
            else:
                raise OSError('Job directory not found')

        except (OSError, ValueError) as error:
            message = str(error)
            success = 0

        return { "success":success, "message":message, "name":name, "config_json":contents }


    def create_job(self, new_name, json_text):
        """ Adds a job """
        message = "Job created successfully"
        success = 1

        try:

            # Generate path and file name
            job_dir = self.jobs_path + "/" + new_name
            job_filename = job_dir + "/" + self.job_config_filename

            # Bail if
            if os.path.exists(job_dir):
                raise SystemError('Job directory already exists')
            else:
                os.mkdir(job_dir)

            # Create Json array for _write_job_file
            if isinstance(json_text, str):
                json_text = ast.literal_eval(json_text)

            if not json_text['description']:
                raise ValueError('Missing description')

            if not json_text['steps']:
                raise ValueError('Missing steps')

            json_text['runNumber'] = 0
            json_text['lastSuccessfulRun'] = 0
            json_text['lastFailedRun'] = 0
            json_text['name'] = new_name

            # Create job file
            self._write_job_file(job_filename, json_text)

        except (ValueError, SystemError) as error:
            message = str(error)
            success = 0

        ret = {"success":success, "message":message}

        return ret


    def update_job(self, name):
        """ Update an existing job """
        success = 1
        message = "-- Under Construction --"
        job_filename = "Placeholder"

        # Remove existing job conf
        if os.path.exists(job_filename):
            self._dirty_rm_rf(job_filename)

        return { "success":success, "message":message }


    def run_job(self, name):
        """ Run a specific job """
        success = 1
        message = "Run successful"
        return_code = 0

        # Construct job directory and file path names
        job_dir = self.jobs_path + "/" + name
        job_config_json_file = job_dir + "/" + "config.json"

        # Generate a tmp directory to work in
        # Use uuid4() because it creates a truly random uuid
        # and doesnt require any arguments and uuid1 uses
        # the system network addr.
        tmp_cwd = "/tmp/viki-" + str(uuid.uuid4())
        os.mkdir(tmp_cwd)

        try:

            # Check job directory exists
            # Otherwise raise OSError
            if not os.path.isdir(job_dir):
                raise OSError('Job not found')

            # Check config json file exists
            # Otherwise raise OSError
            if not os.path.isfile(job_config_json_file):
                raise OSError('Job file not found')

            # Read the file and load the json inside it
            # Otherwise raise OSError
            job_json = json.loads(self._read_job_file(job_config_json_file))
            if job_json is False or job_json is None:
                raise OSError('Job file could not be read')

            # Create filename path for output file
            # todo: Move this to store the output in each individual build dir
            filename = job_dir + "/" + "output.txt"

            # Grab the json array "steps" from jobs/<jobName>/config.json
            jobSteps = job_json['steps']

            # Execute them individually
            # If any of these steps fail then we stop execution
            for step in jobSteps:
                successBool, return_code = self._run_shell_command(step, filename)

                # If unsuccessful stop execution
                if not successBool:
                    raise SystemError('Build step failed')


        except (OSError, subprocess.CalledProcessError, SystemError) as error:
            message = str(error)
            success = 0
        except KeyError:
            message = 'Job has no steps'
            success = 0

        # Clean up tmp workdir
        self._dirty_rm_rf(tmp_cwd)

        return { "success":success, "message":message, "return_code":return_code }

    def delete_job(self, name):
        """ Removes a job by name
        Takes a job's name and removes the directory that the job lives in
        """
        success = 1
        message = "Job deleted"

        try:

            if name is None:
                raise ValueError('Missing job name')

            job_dir = self.jobs_path + '/' + name

            # Check job directory exists
            # Otherwise raise OSError
            if not os.path.isdir(job_dir):
                raise OSError('Job not found')

            # Remove the job directory
            self._dirty_rm_rf(job_dir)

        except (OSError, ValueError) as error:
            message = str(error)
            success = 0

        return { "success":success, "message":message }
