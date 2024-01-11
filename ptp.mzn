include "cumulative.mzn";
% Variables
int: max_wait_time;

% Places
int: n_p;
set of int: n_places = 0..n_p-1;

array[n_places, n_places] of int: dist_matrix; % distance between locations

% Requests
int: n_r;
set of int: n_requests = 0..n_r-1;

array[n_requests] of int: ids_r;
int: id0_r = min(ids_r);

array[n_requests] of int: org_r;  % origin place
array[n_requests] of int: dst_r;  % destination place
array[n_requests] of int: ret_r;  % return place
array[n_requests] of int: srv_r;  % embark/disenbark time
array[n_requests] of int: l_r;    % required seats in vehicle
array[n_requests] of int: rdv_r;  % time at which health care service begins
array[n_requests] of int: drdv_r; % health care service duration
array[n_requests] of int: c_r;    % category (wheelchair, without, ...)

% Activities
int: n_a;
set of int: n_activities = 0..n_a-1;

array[n_activities] of int: ids_a; % activity id
array[n_activities] of int: rids_a; % activity request id
array[n_activities] of int: raids_a; % activity reverse activity id
array[n_activities] of int: dir_a; % activity direction (Forward or Backward)
array[n_activities] of int: org_a; % activity origin location
array[n_activities] of int: dst_a; % activity destination location
array[n_activities] of int: l_a; % required seats in vehicle

% Vehicles
bool: svb; % same vehicle back

set of int: n_categories = 0..2;

int: n_v;
set of int: n_vehicles = 0..n_v-1;

array[n_vehicles] of int: ids_v;              % vehicle id
array[n_vehicles] of int: k_v;                % capacity
array[n_vehicles, n_categories] of bool: C_v; % set of categories
array[n_vehicles] of int: sd_v;               % starting depot
array[n_vehicles] of int: ed_v;               % end depot
array[n_vehicles] of int: savail_v;           % shift start time
array[n_vehicles] of int: eavail_v;           % shift end time

% Decision Variables
% Requests
array[n_requests] of var bool: S_r; % eq 4.2 selected requests

% Activities
array[n_activities] of var int: s_a;        % start
array[n_activities] of var int: d_a;        % duration
array[n_activities] of var int: e_a;        % end
array[n_activities] of var bool: x_a;       % completed (bool -> eq 4.6: 4)
array[n_activities] of var n_vehicles: v_a; % vehicles
array[n_activities, n_vehicles] of var int: d_av; % activity duration of the selected vehicle 

% Constraints
constraint forall(a in n_activities)(if(dir_a[a] == 1)  % Forward Activities
                                        then((s_a[a] >= rdv_r[rids_a[a] - id0_r] - max_wait_time /\ s_a[a] <= rdv_r[rids_a[a] - id0_r]) /\  % eq 4.6: 1
                                             (e_a[a] >= rdv_r[rids_a[a] - id0_r] - max_wait_time /\ e_a[a] <= rdv_r[rids_a[a] - id0_r]))    % eq 4.6: 2
                                           
                                                        % Backward Activities
                                        else((s_a[a] >= rdv_r[rids_a[a] - id0_r] + drdv_r[rids_a[a] - id0_r] /\ 
                                              s_a[a] <= rdv_r[rids_a[a] - id0_r] + drdv_r[rids_a[a] - id0_r] + max_wait_time) /\  % eq 4.6: 6
                                             (e_a[a] >= rdv_r[rids_a[a] - id0_r] + drdv_r[rids_a[a] - id0_r] /\ 
                                              e_a[a] <= rdv_r[rids_a[a] - id0_r] + drdv_r[rids_a[a] - id0_r] + max_wait_time))    % eq 4.6: 7
                                     endif);   

constraint forall(a in n_activities)(d_a[a] >= 0);                % ensure positive duration
constraint forall(a in n_activities)(d_a[a] == e_a[a] - s_a[a]);  % eq 4.6: 3 (duration)

constraint forall(a in n_activities)(if(C_v[v_a[a], c_r[rids_a[a] - id0_r]]) % eq 4.6: 5 (compatible category)
                                      then(x_a[a] == true)
                                      else(x_a[a] == false)
                                    endif);  

constraint forall(a in n_activities, v in n_vehicles)(if(v_a[a] == v)  % selected vehicle
                                                        then(d_av[a,v] == d_a[a])
                                                        else(d_av[a,v] == 0) 
                                                      endif);
                                                      
constraint forall(a in n_activities, v in n_vehicles)(d_av[a,v] >= 0); % ensure positive duration

constraint forall(a in n_activities) (sum(v in n_vehicles)(d_av[a,v]) == d_a[a]); % ensure that the activity only selects one vehicle

constraint forall(a in n_activities)(if(x_a[a] /\ x_a[raids_a[a]]) % eq 4.7 (select request only if Forward Activity and Backwards Actrivity are 1)
                                      then (S_r[rids_a[a] - id0_r] == true) 
                                      else (S_r[rids_a[a] - id0_r] == false) 
                                     endif);  

constraint forall(a in n_activities)(x_a[a] == x_a[raids_a[a]]);  % eq 4.8 (same as eq 4.7 - used for pruning)

constraint forall(i in n_activities, j in n_activities)(if(i != j)  % eq 4.9 (see docs/correct_formulation.png)
                                                          then(if(v_a[i] == v_a[j]) 
                                                                then((s_a[j] - s_a[i] >= dist_matrix[org_a[i],org_a[j]] + srv_r[rids_a[i] - id0_r] \/ 
                                                                      s_a[i] - s_a[j] >= dist_matrix[org_a[j],org_a[i]] + srv_r[rids_a[j] - id0_r]) 
                                                                     /\
                                                                     (s_a[j] - e_a[i] >= dist_matrix[dst_a[i],org_a[j]] \/
                                                                      e_a[i] - s_a[j] >= dist_matrix[org_a[j],dst_a[i]] + srv_r[rids_a[j] - id0_r] + srv_r[rids_a[i] - id0_r])
                                                                     /\
                                                                     (e_a[j] - s_a[i] >= dist_matrix[org_a[i],dst_a[j]] + srv_r[rids_a[i] - id0_r] + srv_r[rids_a[j] - id0_r] \/
                                                                      s_a[i] - e_a[j] >= dist_matrix[dst_a[j],org_a[i]])
                                                                     /\
                                                                     (e_a[j] - e_a[i] >= dist_matrix[dst_a[i],dst_a[j]] + srv_r[rids_a[j] - id0_r] \/
                                                                      e_a[i] - e_a[j] >= dist_matrix[dst_a[j],dst_a[i]] + srv_r[rids_a[i] - id0_r]))
                                                               endif)
                                                        endif);

constraint forall(a in n_activities)(d_a[a] >= dist_matrix[org_a[a], dst_a[a]] + 2 * srv_r[rids_a[a] - id0_r]); % eq 4.10

constraint forall(v in n_vehicles)(cumulative(s_a, d_av[..,v], l_a, k_v[v])); % eq 4.11

constraint forall(a in n_activities)(s_a[a] >= savail_v[v_a[a]] + dist_matrix[sd_v[v_a[a]], org_a[a]] /\
                                     e_a[a] <= eavail_v[v_a[a]] - dist_matrix[dst_a[a], ed_v[v_a[a]]]); % eq 4.12

constraint if svb then forall(a in n_activities)(ids_v[v_a[a]] == ids_v[v_a[raids_a[a]]]) endif;  % eq 4.17 (same vehicle back)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
% Solve
solve maximize sum(S_r);  % eq 4.14 (maximize the number of served requests)