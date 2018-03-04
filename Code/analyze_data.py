import argparse
import csv
import os
import re
import matplotlib.pyplot as plt

class Experiment(object):
    def __init__(self, params, means_data, sterrs_data):
        self.params = params
        self.means_data = means_data
        self.sterrs_data = sterrs_data

    def __str__(self):
        return 'Experiment: ' + str(self.params)

def maybe_num(x):
    """Converts string x to an int if possible, otherwise a float if possible,
    otherwise returns it unchanged."""
    try: return int(x)
    except ValueError:
        try: return float(x)
        except ValueError: return x

def concat(folder, element):
    """folder and element are strings"""
    if folder[-1] == '/':
        return folder + element
    return folder + '/' + element

def get_param_vals(folder_name):
    """Gets the parameter values of the experiment from its folder name.

    folder_name is a string such as "2018-03-02 13:17:51.-beta=0.1-dim=10-dist_scale=0.5-gamma=1.0-mdp=gridworld-num_exp=100-num_iter=20-num_iters_optim=10-num_q_max=500-num_states=100-num_traject=1-qsize=10-seed=1-size_proxy=100-size_true=10000-value_iters=25"
    Returns two things:
    - A tuple of tuples of strings/numbers, of the form ((key, value), ...)
    - A dictionary mapping strings to strings or numbers, of the form
      {key : value, ...}
    """
    key_vals = re.finditer(r"([^-]+)=([^-]+)", folder_name)
    result_tuple = tuple(((m.group(1), maybe_num(m.group(2))) for m in key_vals))
    result_dict = { k:v for k, v in result_tuple }
    return result_tuple, result_dict

def load_experiment_file(filename):
    """Loads the data from <filename>, which should be an all choosers CSV.

    Returns two things:
    - chooser: A string, which chooser was used for this experiment
    - data: Dictionary mapping keys (such as test_entropy) to lists of numbers.
    """
    with open(filename, 'r') as csvfile:
        chooser = csvfile.readline().strip().strip(',')
        reader = csv.DictReader(csvfile)
        first_row = next(reader)
        data = { k:[maybe_num(v)] for k, v in first_row.items() }
        for row in reader:
            for k, v in row.items():
                data[k].append(maybe_num(v))
    return chooser, data

def load_experiment(folder):
    """Loads the data from <folder>, specifically from all choosers-means-.csv
    and all choosers-sterr-.csv.

    Returns three things:
    - chooser: A string, which chooser was used for this experiment
    - means_data: Dictionary mapping keys to lists of numbers (means).
    - sterr_data: Dictionary mapping keys to lists of numbers (std errors).
    """
    means_chooser, means_data = load_experiment_file(
        concat(folder, 'all choosers-means-.csv'))
    sterrs_chooser, sterrs_data = load_experiment_file(
        concat(folder, 'all choosers-sterr-.csv'))
    assert means_chooser == sterrs_chooser
    return means_chooser, means_data, sterrs_data

def simplify_keys(experiments):
    """Identifies experiment parameters that are constant across the dataset and
    removes them from the keys, leaving shorter, simpler keys.

    experiments: Dictionary from keys of the form ((var, val), ...) to
        Experiment objects
    Returns two things:
      - new_experiments: Same type as experiments, but with smaller keys
      - controls: Dictionary of the form {var : val} containing the parameters and
          their values that did not change over the experiments.
    """
    keys = list(experiments.keys())
    first_key = keys[0]

    indices_with_no_variation = []
    indices_with_variation = []
    for index in range(len(first_key)):
        if all(key[index] == first_key[index] for key in keys):
            indices_with_no_variation.append(index)
        else:
            indices_with_variation.append(index)

    def simple_key(key):
        return tuple((key[index] for index in indices_with_variation))

    new_experiments = {simple_key(k):v for k, v in experiments.items()}
    controls = dict([first_key[index] for index in indices_with_no_variation])
    return new_experiments, controls

def fix_special_cases(experiments):
    """Does postprocessing to handle any special cases.

    For example, the full chooser is only run with query size 2 since it doesn't
    depend on query size, but we want it to be plotted with all the other
    queries as well, so we duplicate the experiment with other query sizes.

    - experiments: Dictionary from keys of the form ((var, val), ...) to
          Experiment objects
    """
    query_sizes = set([exp.params['qsize'] for exp in experiments.values()])
    full_exps = [(key, exp) for key, exp in experiments.items() if exp.params['choosers'] == 'full']
    def replace(key_tuple, var, val):
        return tuple(((k, (val if k == var else v)) for k, v in key_tuple))

    for key, exp in full_exps:
        for qsize in query_sizes:
            new_key = replace(key, 'qsize', qsize)
            if new_key not in experiments:
                new_params = dict(exp.params.items())
                new_params['qsize'] = qsize
                experiments[new_key] = Experiment(
                    new_params, exp.means_data, exp.sterrs_data)

def load_data(folder):
    """Loads all experiment data from data/<folder>.

    Returns three things:
    - experiments: Dictionary from keys of the form ((var, val), ...) to
          Experiment objects
    - changing_vars: List of strings, the variables that have more than one
          distinct value across Experiments
    - control_var_vals: Dictionary of the form {var : val} containing the
          parameters and their values that did not change over the experiments.
    """
    folder = concat('data', folder)
    experiments = {}
    for experiment in os.listdir(folder):
        if not experiment.startswith('2018'):
            continue
        key, params_dict = get_param_vals(experiment)
        chooser, means, sterrs = load_experiment(concat(folder, experiment))
        if 'choosers' in params_dict:
            assert chooser == params_dict['choosers']
        else:
            key = key + (('choosers', chooser),)
            params_dict['choosers'] = chooser
        experiments[key] = Experiment(params_dict, means, sterrs)
    experiments, control_var_vals = simplify_keys(experiments)
    fix_special_cases(experiments)
    changing_vars = [var for var, val in experiments.keys()[0]]
    return experiments, changing_vars, control_var_vals

def graph_all(experiments, all_vars, x_var, dependent_vars, independent_vars,
              controls, folder):
    """Graphs data and saves them.

    Each graph generated plots the dependent_vars against x_var for all
    valuations of independent_vars, with the control variables set to the values
    specified in controls. For every valuation of variables not in x_var,
    dependent_vars, independent_vars, or controls, a separate graph is
    generated and saved in folder.

    - experiments: Dictionary from keys of the form ((var, val), ...) to
          Experiment objects
    - all_vars: List of strings, all the variables that have some variation
    - x_var: Variable that provides the data for the x-axis
    - dependent_vars: List of strings, variables to plot on the y-axis
    - independent_vars: List of strings, experimental conditions to plot on the
          same graph
    - controls: Tuple of the form ((var, val), ...) where var is a string and
          val is a string or number. The values of control variables.
    - folder: Graphs are saved to graph/<folder>/
    """
    control_vars = [var for var, val in controls]
    vars_so_far = [x_var] + dependent_vars + independent_vars + control_vars
    remaining_vars = list(set(all_vars) - set(vars_so_far))
    graphs_data = {}

    for experiment in experiments.values():
        params = experiment.params
        if not all(params[k] == v for k, v in controls):
            continue

        key = ','.join(['{0}={1}'.format(k, params[k]) for k in remaining_vars])
        if key not in graphs_data:
            graphs_data[key] = []
        graphs_data[key].append(experiment)

    for key, exps in graphs_data.items():
        graph(exps, x_var, dependent_vars, independent_vars, controls, key, folder)

def graph(experiments, x_var, dependent_vars, independent_vars, controls,
          other_vals, folder):
    """Creates and saves a single graph.

    Arguments are almost the same as for graph_all.
    - other_vals: String of the form "{var}={val},..." specifying values of
          variables not in x_var, dependent_vars, independent_vars, or
          controls.
    """
    assert len(dependent_vars) == 1
    y_var = dependent_vars[0]

    plt.figure()
    for experiment in experiments:
        params = experiment.params
        means, sterrs = experiment.means_data, experiment.sterrs_data
        label = ', '.join([str(params[k]) for k in independent_vars])
        plt.errorbar(means[x_var], means[y_var], sterrs[y_var], label=label)

    plt.xlabel(x_var)
    plt.ylabel(y_var)

    subtitle = ','.join(['{0}={1}'.format(k, v) for k, v in controls])
    subtitle = '{0},{1}'.format(subtitle, other_vals).strip(',')
    title = 'Data for {0}'.format(', '.join(independent_vars))
    plt.title(title + '\n' + subtitle)
    plt.legend() #loc='best', ncol=2, mode="expand", shadow=True, fancybox=True)

    folder = concat('graph', folder)
    filename = '{0}-vs-{1}-for-{2}-with-{3}.png'.format(
        ','.join(dependent_vars), x_var, ','.join(independent_vars), subtitle)
    if not os.path.exists(folder):
        os.mkdir(folder)
    plt.savefig(concat(folder, filename))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--folder', required=True)
    parser.add_argument('-x', '--x_var', default='iteration')
    parser.add_argument('-d', '--dependent_var', action='append', required=True)
    parser.add_argument('-i', '--independent_var', action='append', required=True)
    parser.add_argument('-c', '--control_var_val', action='append', default=[])
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    experiments, all_vars, _ = load_data(args.folder)
    controls = [kv_pair.split('=') for kv_pair in args.control_var_val]
    controls = [(k, maybe_num(v)) for k, v in controls]
    graph_all(experiments, all_vars, args.x_var, args.dependent_var,
              args.independent_var, controls, args.folder)