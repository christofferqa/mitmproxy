import { combineReducers } from 'redux'
import * as viewActions from './utils/view'
import main from './views/main.js'

export const ADD = 'FLOW_VIEWS_ADD'
export const UPDATE = 'FLOW_VIEWS_UPDATE'
export const REMOVE = 'FLOW_VIEWS_REMOVE'
export const RECEIVE = 'FLOW_VIEWS_RECEIVE'

export default combineReducers({
    main,
})

/**
 * @public
 */
export function add(item) {
    return { type: ADD, item }
}

/**
 * @public
 */
export function update(id, item) {
    return { type: UPDATE, id, item }
}

/**
 * @public
 */
export function remove(id) {
    return { type: REMOVE, id }
}

/**
 * @public
 */
export function receive(list) {
    return { type: RECEIVE, list }
}
