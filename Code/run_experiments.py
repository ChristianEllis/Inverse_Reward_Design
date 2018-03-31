from subprocess import call

# Discrete experiments

NUM_EXPERIMENTS = '100'  # Modify this to change the sample size

# choosers = ['greedy_discrete', 'random']
discr_query_sizes = ['3']
choosers = ['feature_random', 'feature_entropy_search_then_optim', 'feature_entropy_init_none', 'feature_entropy_search', 'feature_entropy_random_init_none']
mdp_types = ['bandits','gridworld']
true_reward_space_sizes = ['1000000']
objectives = ['entropy']
num_iter = '20'     # Maybe do 40 for gridworld
num_q_max = '10000'
# Keeping this bug because our old data had it
square_probs_bug = '1'  # REMOVE PARAMETER FOR NEXT RUN
weights_dist_init = 'normal2'
weights_dist_search = 'normal2'
only_optim_biggest = '1'    # Change back to zero

def run(chooser, qsize, mdp_type, objective='entropy', discretization_size='5', viter='15', rsize='1000000',
        subsampling='1', num_iter='20'):
    if mdp_type == 'bandits':
        # Values range from -5 to 5 approximately, so setting beta to 1 makes
        # the worst Q-value e^10 times less likely than the best one
        beta = '0.5'
        beta_planner = '0.5'
        dim = '20'
        # TODO: Set the following to the right values
        lr = '20.'
        num_iters_optim = '10'
    else:
        # Values range from 50-100 when using 25 value iterations.
        beta = '0.2'                                                    # Set to 0.5 as well to show entropy=0 for qsize-=10?
        beta_planner = '1'
        dim = '20'
        # TODO: Set the following to the right values
        lr = '20'
        num_iters_optim = '10'

    command = ['python', 'run_IRD.py',
                  '-c', chooser,
                  '--query_size', qsize,
                  '--num_experiments', NUM_EXPERIMENTS,
                  '--num_iter', num_iter,
                  '--gamma', '1.',
                  '--size_true_space', rsize,
                  '--size_proxy_space', '100',
                  '--seed', '1',
                  '--beta', beta,
                  '--beta_planner', beta_planner,
                  '--num_states', '100',  # Only applies for bandits
                  '--dist_scale', '0.5',
                  '--num_traject', '1',
                  '--num_queries_max', num_q_max,
                  '--height', '12',  # Only applies for gridworld
                  '--width', '12',   # Only applies for gridworld
                  '--lr', lr,   # Doesn't matter, only applies in continuous case
                  '--num_iters_optim', num_iters_optim,
                  '--value_iters', viter,  # Consider decreasing viters to 10-15 to make the path more important as opposed to ending up at the right goal
                  '--mdp_type', mdp_type,
                  '--feature_dim', dim,
                  '--discretization_size', discretization_size,
                  '--num_test_envs', '100',
                  '--subsampling', subsampling,
                  '--num_subsamples','10000',
                  '--weighting', '1',
                  '--well_spec', '1',
                  '--linear_features', '1',
                  '--objective',objective,
                  '-weights_dist_init', weights_dist_init,
                  '-weights_dist_search', weights_dist_search,
                  '--only_optim_biggest', only_optim_biggest
               ]
    print 'Running command', ' '.join(command)
    call(command)


# Run as usual
def run_discrete():
    for mdp_type in mdp_types:

        for chooser in choosers:
            for qsize in discr_query_sizes:
                run(chooser, qsize, mdp_type, num_iter=num_iter)

        run('full', '2', mdp_type, num_iter=num_iter)

# Run with different rsize and subsampling values
def run_subsampling():
    for mdp_type in mdp_types:
        for rsize in true_reward_space_sizes:
            if rsize == '10000':
                subsampling = '0'
            else: subsampling = '1'


            for objective in objectives:
                for chooser in choosers:
                        for qsize in discr_query_sizes:
                            run(chooser, qsize, mdp_type, objective, rsize=rsize, subsampling=subsampling)
                run('full', '2', mdp_type, objective, rsize=rsize, subsampling=subsampling, num_iter=num_iter)


def run_discrete_optimization():
    for mdp_type in mdp_types:
        for qsize in discr_query_sizes:
            for chooser in ['incremental_optimize', 'joint_optimize']:
                run(chooser, qsize, mdp_type)


def run_continuous():
    for mdp_type in mdp_types:
        for qsize, discretization_size in [('3', '3'), ('2', '5'), ('1', '9')]:
            for chooser in choosers:
                run(chooser, qsize, mdp_type, discretization_size=discretization_size, num_iter=num_iter)

if __name__ == '__main__':
    run_continuous()
